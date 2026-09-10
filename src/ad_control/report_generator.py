from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import uuid
import webbrowser
from datetime import datetime
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .artifact_store import CaseArtifactStore, artifact_root
from .redaction import redact

# Keep strong refs so daemon report servers are not GC'd while still serving.
_REPORT_SERVERS: list[tuple[ThreadingHTTPServer, threading.Thread, str]] = []

_STEP_ATTACHMENT_HINTS = (
    ("创建", ("rule-request.redacted.json", "rule-response.redacted.json")),
    ("造数", ("seed-plan.json", "seed-audit.json", "cleanup-manifest.json")),
    ("写入", ("seed-plan.json", "seed-audit.json", "cleanup-manifest.json")),
    ("管控规则", ("job-response.redacted.json",)),
    ("校验", ("validation-result.json",)),
    ("Cleanup", ("cleanup-result.json",)),
    ("清理", ("cleanup-result.json",)),
)

_CASE_ATTACHMENTS = (
    ("规则请求", "rule-request.redacted.json", "application/json"),
    ("规则响应", "rule-response.redacted.json", "application/json"),
    ("造数计划", "seed-plan.json", "application/json"),
    ("造数审计", "seed-audit.json", "application/json"),
    ("管控规则响应", "job-response.redacted.json", "application/json"),
    ("校验结果", "validation-result.json", "application/json"),
    ("清理结果", "cleanup-result.json", "application/json"),
    ("Markdown 报告", "report/case.md", "text/markdown"),
)


def _to_millis(value: Any, fallback: int) -> int:
    try:
        return int(datetime.fromisoformat(str(value)).timestamp() * 1000)
    except (TypeError, ValueError):
        return fallback


def _allure_status(status: Any) -> str:
    text = str(status or "skipped").lower()
    if text in {"passed", "dry-run"}:
        return "passed"
    if text == "failed":
        return "failed"
    if text in {"broken", "unknown"}:
        return text
    return "skipped"


def _pretty_json(value: Any) -> str:
    return json.dumps(redact(value), ensure_ascii=False, indent=2, default=str)


def _read_store_json(store: CaseArtifactStore, relative: str) -> dict[str, Any] | list[Any] | None:
    path = store.root / relative
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None
    return value


def _write_allure_attachment(
    results_dir: Path,
    *,
    name: str,
    content: str,
    mime_type: str,
    suffix: str,
) -> dict[str, str]:
    attachment_id = str(uuid.uuid4())
    filename = f"{attachment_id}-attachment{suffix}"
    path = results_dir / filename
    path.write_text(content, encoding="utf-8")
    return {"name": name, "source": filename, "type": mime_type}


def _attach_existing_file(
    store: CaseArtifactStore,
    results_dir: Path,
    *,
    name: str,
    relative: str,
    mime_type: str,
) -> dict[str, str] | None:
    path = store.root / relative
    if not path.exists() or not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError:
        return None
    suffix = path.suffix if path.suffix else ".txt"
    if mime_type == "application/json":
        try:
            text = _pretty_json(json.loads(text))
            suffix = ".json"
        except json.JSONDecodeError:
            mime_type = "text/plain"
            suffix = ".txt"
    return _write_allure_attachment(
        results_dir,
        name=name,
        content=text,
        mime_type=mime_type,
        suffix=suffix,
    )


def _step_details_message(step: dict[str, Any]) -> str:
    details = {key: value for key, value in step.items() if key not in {"name", "status", "message"}}
    chunks: list[str] = []
    message = step.get("message")
    if message not in (None, ""):
        chunks.append(str(message))
    if details:
        chunks.append(_pretty_json(details))
    return "\n\n".join(chunks)


def _build_description(result: dict[str, Any], store: CaseArtifactStore) -> str:
    seed = _read_store_json(store, "seed-plan.json") or {}
    validation = _read_store_json(store, "validation-result.json") or {}
    lines = [
        f"## {result.get('name') or result.get('case_id')}",
        "",
        f"- Case: `{result.get('case_id')}`",
        f"- Mode: `{result.get('mode')}`",
        f"- Run: `{result.get('run_id')}`",
        f"- Rule ID: `{result.get('rule_id') or '-'}`",
        f"- Rule name: `{result.get('rule_name') or '-'}`",
        f"- Status: `{result.get('status')}` / cleanup `{result.get('cleanup_status')}`",
        "",
        "### Flow",
    ]
    for index, step in enumerate(result.get("steps") or [], start=1):
        lines.append(f"{index}. **{step.get('name', 'step')}** — `{step.get('status', 'unknown')}`")
    if isinstance(seed, dict) and seed:
        lines.extend(
            [
                "",
                "### Seed",
                f"- Table: `{seed.get('table', '-')}`",
                f"- Channel: `{seed.get('channel_code', '-')}`",
                f"- Rows: `{len(seed.get('rows') or [])}`",
                f"- Strategy: `{seed.get('row_strategy', '-')}`",
            ]
        )
        for condition in seed.get("conditions") or []:
            lines.append(
                f"- Condition: `{condition.get('column')}` {condition.get('compare_type')} "
                f"{condition.get('val1')} ({condition.get('effective_mode')})"
            )
    if isinstance(validation, dict) and validation:
        lines.extend(
            [
                "",
                "### Validation",
                f"- Matched: `{validation.get('matched', 'n/a')}`",
                f"- Match count: `{validation.get('match_count', '-')}`",
                f"- Observe: `{validation.get('observed_s', validation.get('observe_s', '-'))}`",
                f"- Polls: `{validation.get('polls', '-')}`",
            ]
        )
    return "\n".join(lines)


def write_allure_result(store: CaseArtifactStore, result: dict[str, Any]) -> Path:
    now = int(time.time() * 1000)
    started = _to_millis(result.get("started_at"), now)
    stopped = max(started, _to_millis(result.get("finished_at"), now))
    status = _allure_status(result.get("status"))
    identity = f"{result.get('run_id', '')}:{result.get('case_id', '')}:{result.get('mode', '')}"
    result_uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, identity))
    results_dir = store.allure_results
    results_dir.mkdir(parents=True, exist_ok=True)

    # Drop previous generated payloads for this case/mode so regenerate stays clean.
    for stale in results_dir.glob("*-result.json"):
        try:
            stale.unlink()
        except OSError:
            pass
    for stale in results_dir.glob("*-attachment*"):
        try:
            stale.unlink()
        except OSError:
            pass

    case_attachments: list[dict[str, str]] = []
    attachment_by_relative: dict[str, dict[str, str]] = {}
    for name, relative, mime in _CASE_ATTACHMENTS:
        attachment = _attach_existing_file(
            store,
            results_dir,
            name=name,
            relative=relative,
            mime_type=mime,
        )
        if attachment:
            case_attachments.append(attachment)
            attachment_by_relative[relative] = attachment

    steps: list[dict[str, Any]] = []
    step_count = max(1, len(result.get("steps") or []))
    span = max(1, stopped - started)
    for index, step in enumerate(result.get("steps") or []):
        step_start = started + int(span * index / step_count)
        step_stop = started + int(span * (index + 1) / step_count)
        step_attachments: list[dict[str, str]] = []
        step_name = str(step.get("name") or "step")
        for hint, relatives in _STEP_ATTACHMENT_HINTS:
            if hint in step_name:
                for relative in relatives:
                    attachment = attachment_by_relative.get(relative)
                    if attachment:
                        step_attachments.append(attachment)
                break
        details_message = _step_details_message(step if isinstance(step, dict) else {})
        steps.append(
            {
                "name": step_name,
                "status": _allure_status(step.get("status")),
                "stage": "finished",
                "start": step_start,
                "stop": max(step_start + 1, step_stop),
                "statusDetails": {"message": details_message},
                "attachments": step_attachments,
                "parameters": [
                    {"name": key, "value": str(value)}
                    for key, value in sorted(step.items())
                    if key not in {"name", "status", "message"} and value not in (None, "")
                ],
            }
        )

    body = {
        "uuid": result_uuid,
        "historyId": f"{result.get('case_id', '')}:{result.get('mode', '')}",
        "testCaseId": f"{result.get('case_id', '')}:{result.get('mode', '')}",
        "name": f"{result.get('name', result.get('case_id', ''))} [{result.get('mode', '')}]",
        "fullName": f"ad-control.{result.get('case_id', '')}.{result.get('mode', '')}",
        "description": _build_description(result, store),
        "status": status,
        "stage": "finished",
        "start": started,
        "stop": stopped,
        "statusDetails": {
            "message": str(result.get("error") or ""),
            "trace": str(result.get("cleanup_error") or ""),
        },
        "labels": [
            {"name": "framework", "value": "ad-control"},
            {"name": "language", "value": "python"},
            {"name": "parentSuite", "value": str(result.get("run_id") or "run")},
            {"name": "suite", "value": str(result.get("case_id") or "case")},
            {"name": "subSuite", "value": str(result.get("mode") or "mode")},
            {"name": "feature", "value": "广告管控集成流程"},
            {"name": "story", "value": str(result.get("name") or result.get("case_id") or "")},
            {"name": "case", "value": str(result.get("case_id", ""))},
            {"name": "mode", "value": str(result.get("mode", ""))},
            {"name": "severity", "value": "normal"},
            {"name": "tag", "value": str(result.get("mode") or "")},
        ],
        "parameters": [
            {"name": "run_id", "value": str(result.get("run_id", ""))},
            {"name": "rule_id", "value": str(result.get("rule_id") or "-")},
            {"name": "rule_name", "value": str(result.get("rule_name") or "-")},
            {"name": "cleanup", "value": str(result.get("cleanup_status") or "-")},
        ],
        "links": [],
        "steps": steps,
        "attachments": case_attachments,
    }
    path = results_dir / f"{result_uuid}-result.json"
    path.write_text(json.dumps(redact(body), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def write_markdown(store: CaseArtifactStore, result: dict[str, Any]) -> Path:
    result = redact(result)

    def read_json(name: str) -> dict[str, Any]:
        path = store.root / name
        if not path.exists():
            return {}
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    rule_request = read_json("rule-request.redacted.json")
    rule_response = read_json("rule-response.redacted.json")
    seed_plan = read_json("seed-plan.json")
    job_response = read_json("job-response.redacted.json")
    validation = read_json("validation-result.json")
    cleanup = read_json("cleanup-result.json")
    try:
        duration_s = (
            datetime.fromisoformat(str(result.get("finished_at")))
            - datetime.fromisoformat(str(result.get("started_at")))
        ).total_seconds()
    except (TypeError, ValueError):
        duration_s = None
    lines = [
        f"# Ad Control Case Report: {result.get('name', result.get('case_id', ''))}",
        "",
        f"- Case: `{result.get('case_id', '')}`",
        f"- Mode: `{result.get('mode', '')}`",
        f"- Run ID: `{result.get('run_id', '')}`",
        f"- Rule name: `{result.get('rule_name') or '-'}`",
        f"- Rule ID: `{result.get('rule_id') or '-'}`",
        f"- Status: **{result.get('status', 'unknown')}**",
        f"- Cleanup: **{result.get('cleanup_status', 'unknown')}**",
        f"- Started: `{result.get('started_at') or '-'}`",
        f"- Finished: `{result.get('finished_at') or '-'}`",
        f"- Duration: `{f'{duration_s:.3f}s' if duration_s is not None else '-'}`",
        "",
        "## Flow steps",
        "",
        "| Step | Status | Details |",
        "|---|---|---|",
    ]
    for step in result.get("steps", []):
        details = {key: value for key, value in step.items() if key not in {"name", "status"}}
        message = json.dumps(details, ensure_ascii=False, default=str).replace("|", "\\|").replace("\n", " ") if details else ""
        lines.append(f"| {step.get('name', 'step')} | {step.get('status', 'unknown')} | {message} |")
    response_summary = job_response.get("body")
    if isinstance(response_summary, (dict, list)):
        response_summary = json.dumps(response_summary, ensure_ascii=False, default=str)[:500]
    lines.extend([
        "",
        "## API summary",
        "",
        f"- Create request fields: `{', '.join(sorted(rule_request)) if rule_request else '-'}`",
        f"- Create response keys: `{', '.join(sorted(rule_response)) if rule_response else '-'}`",
        f"- 管控规则 status: `{job_response.get('status', '-')}`",
        f"- 管控规则 elapsed: `{job_response.get('elapsed_ms', '-')} ms`",
        f"- 管控规则 URL: `{job_response.get('url', '-')}`",
        f"- 管控规则 response: `{response_summary if response_summary not in (None, '') else '-'}`",
        "",
        "## Seed summary",
        "",
        f"- Table: `{seed_plan.get('table', '-')}`",
        f"- Time grain: `{seed_plan.get('time_grain', '-')}`",
        f"- Rows: `{len(seed_plan.get('rows', []) or [])}`",
        f"- Formula status: `{seed_plan.get('formula_status', '-')}`",
        "",
        "### Conditions",
        "",
        "| Metric | Compare | Value | Reduce | Time | Expected | Scenario |",
        "|---|---|---|---|---|---|---|",
    ])
    for condition in seed_plan.get("conditions", []) or []:
        values = condition.get("val1") if condition.get("val2") in (None, "") else f"{condition.get('val1')}..{condition.get('val2')}"
        lines.append(
            f"| {condition.get('column', '-')} | {condition.get('compare_type', '-')} | {values} | "
            f"{condition.get('reduce_type', '-')} | {condition.get('time_type', '-')} | "
            f"{condition.get('effective_mode', '-')} | {condition.get('scenario_key', '-')} |"
        )
    lines.extend([
        "",
        "## Validation summary",
        "",
        f"- Validation status: `{validation.get('status', '-')}`",
        f"- Match status: `{validation.get('matched', 'n/a')}`",
        f"- HIT match count: `{validation.get('match_count', 0)}`",
        f"- MISS configured observation: `{validation.get('observe_s', '-')} s`",
        f"- MISS actual observation: `{validation.get('observed_s', '-')} s`",
        f"- Poll count: `{validation.get('polls', '-')}`",
        "",
        "## Cleanup summary",
        "",
        f"- Cleanup status: `{cleanup.get('status', result.get('cleanup_status', '-'))}`",
        f"- Inserted rows: `{cleanup.get('inserted_rows', '-')}`",
        f"- Deleted rows: `{cleanup.get('deleted_rows', '-')}`",
        f"- Remaining rows: `{cleanup.get('remaining_rows', '-')}`",
    ])
    if result.get("error"):
        lines.extend(["", "## Main flow failure", "", "```text", str(result["error"]), "```"])
    if result.get("cleanup_error"):
        lines.extend(["", "## Cleanup failure", "", "```text", str(result["cleanup_error"]), "```"])
    lines.extend(["", "## Artifacts", ""])
    for key, value in sorted(result.get("artifacts", {}).items()):
        lines.append(f"- `{key}`: `{value}`")
    return store.write_text("report/case.md", "\n".join(lines) + "\n")


def _resolve_allure_command() -> list[str] | None:
    """Return an argv prefix that can launch Allure on the current OS."""
    # On Windows shutil.which("allure") often resolves to the extensionless Unix
    # launcher, which Python cannot CreateProcess. Prefer the .bat wrapper.
    if os.name == "nt":
        for candidate in ("allure.bat", "allure.cmd", "allure.exe"):
            path = shutil.which(candidate)
            if path:
                return [path]
        path = shutil.which("allure")
        if path and path.lower().endswith((".bat", ".cmd", ".exe")):
            return [path]
        if path:
            bat = Path(path + ".bat")
            if bat.exists():
                return [str(bat)]
            # Last resort: let cmd.exe resolve "allure" via PATHEXT.
            return ["cmd.exe", "/c", "allure"]
    path = shutil.which("allure")
    return [path] if path else None


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def _pick_free_port(host: str = "127.0.0.1") -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def serve_report_directory(
    report_dir: str | Path,
    *,
    host: str | None = None,
    port: int | None = None,
    open_browser: bool | None = None,
) -> str:
    """Serve an Allure report directory over HTTP and return the index URL.

    Browsers block multi-file Allure under ``file://``. A localhost HTTP URL is
    the reliable way to open reports; single-file HTML also works via this URL.
    """
    directory = Path(report_dir).resolve()
    if not directory.is_dir():
        raise ValueError(f"report directory does not exist: {directory}")
    index = directory / "index.html"
    if not index.exists():
        raise ValueError(f"report index.html missing: {index}")

    bind_host = (host or os.getenv("AD_CONTROL_ALLURE_HOST") or "127.0.0.1").strip() or "127.0.0.1"
    bind_port = port if port is not None else int(os.getenv("AD_CONTROL_ALLURE_PORT") or "0")
    if bind_port <= 0:
        bind_port = _pick_free_port(bind_host)

    handler = partial(SimpleHTTPRequestHandler, directory=str(directory))
    server = ThreadingHTTPServer((bind_host, bind_port), handler)
    thread = threading.Thread(target=server.serve_forever, name=f"allure-http-{bind_port}", daemon=True)
    thread.start()
    url = f"http://{bind_host}:{bind_port}/index.html"
    _REPORT_SERVERS.append((server, thread, url))

    url_file = directory.parent / "allure-url.txt"
    try:
        url_file.write_text(url + "\n", encoding="utf-8")
    except OSError:
        pass

    should_open = _env_flag("AD_CONTROL_ALLURE_OPEN_BROWSER", True) if open_browser is None else bool(open_browser)
    if should_open:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    return url


def publish_allure_report(
    index_html: str | Path,
    *,
    serve: bool | None = None,
    open_browser: bool | None = None,
    detach: bool | None = None,
) -> dict[str, str]:
    """Return file path and optional localhost URL for an Allure index.html.

    When ``detach`` is true (default outside tests), a separate Python process
    keeps serving so the URL survives after the caller exits.
    """
    index = Path(index_html).resolve()
    result = {
        "allure_html": str(index),
        "allure_url": "",
    }
    should_serve = _env_flag("AD_CONTROL_ALLURE_SERVE", True) if serve is None else bool(serve)
    if not (should_serve and index.exists()):
        return result

    should_detach = _env_flag("AD_CONTROL_ALLURE_DETACH", True) if detach is None else bool(detach)
    should_open = _env_flag("AD_CONTROL_ALLURE_OPEN_BROWSER", True) if open_browser is None else bool(open_browser)
    if should_detach:
        result["allure_url"] = start_detached_report_server(index.parent, open_browser=should_open)
    else:
        result["allure_url"] = serve_report_directory(index.parent, open_browser=should_open)
    return result


def start_detached_report_server(
    report_dir: str | Path,
    *,
    open_browser: bool = True,
    host: str | None = None,
    port: int | None = None,
) -> str:
    """Spawn ``scripts/serve_allure_http.py`` in a detached process and return its URL."""
    directory = Path(report_dir).resolve()
    index = directory / "index.html"
    if not index.exists():
        raise ValueError(f"report index.html missing: {index}")

    bind_host = (host or os.getenv("AD_CONTROL_ALLURE_HOST") or "127.0.0.1").strip() or "127.0.0.1"
    bind_port = port if port is not None else int(os.getenv("AD_CONTROL_ALLURE_PORT") or "0")
    if bind_port <= 0:
        bind_port = _pick_free_port(bind_host)

    # report_generator.py lives at <repo>/src/ad_control/...
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "scripts" / "serve_allure_http.py"
    if not script.exists():
        raise FileNotFoundError(f"serve helper missing: {script}")
    url_file = directory.parent / "allure-url.txt"
    pid_file = directory.parent / "allure-server.pid"
    log_file = directory.parent / "allure-server.log"
    for path in (url_file, pid_file):
        try:
            if path.exists():
                path.unlink()
        except OSError:
            pass

    cmd = [
        sys.executable,
        str(script),
        "--report-dir",
        str(directory),
        "--host",
        bind_host,
        "--port",
        str(bind_port),
        "--pid-file",
        str(pid_file),
    ]
    if not open_browser:
        cmd.append("--no-open")

    log_handle = log_file.open("w", encoding="utf-8")
    popen_kwargs: dict[str, Any] = {
        "cwd": str(repo_root),
        "stdout": log_handle,
        "stderr": subprocess.STDOUT,
        # Keep the log handle open for the child; do not close_fds on Windows
        # when redirecting stdout to a file handle.
        "close_fds": False,
    }
    if os.name == "nt":
        # Detach from the current console so parent exit does not kill the server.
        creationflags = getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
        creationflags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
        popen_kwargs["creationflags"] = creationflags
    else:
        popen_kwargs["start_new_session"] = True

    subprocess.Popen(cmd, **popen_kwargs)  # noqa: S603 - local helper script
    try:
        log_handle.close()
    except OSError:
        pass
    url = f"http://{bind_host}:{bind_port}/index.html"
    deadline = time.time() + 8
    while time.time() < deadline:
        if url_file.exists():
            text = url_file.read_text(encoding="utf-8").strip()
            if text.startswith("http://"):
                url = text
                break
        # Fallback probe: accept connection even if url file is delayed.
        try:
            with socket.create_connection((bind_host, bind_port), timeout=0.3):
                url_file.write_text(url + "\n", encoding="utf-8")
                break
        except OSError:
            time.sleep(0.1)
    else:
        raise RuntimeError(f"detached Allure server did not become ready; see {log_file}")

    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    return url


def generate_allure_html(
    store: CaseArtifactStore | None = None,
    *,
    results_dir: Path | None = None,
    report_dir: Path | None = None,
    use_cli: bool = False,
    single_file: bool | None = None,
) -> Path:
    """Generate Allure HTML.

    Aggregated CLI reports default to ``--single-file``. Prefer opening via the
    HTTP URL from ``publish_allure_report`` / ``generate_run_allure_report``;
    ``file://`` is unreliable for multi-file Allure and some browser policies.
    """
    source = Path(results_dir or (store.allure_results if store else ""))
    target = Path(report_dir or (store.allure_report if store else ""))
    if not source or not target:
        raise ValueError("results_dir/report_dir or store is required")
    target.mkdir(parents=True, exist_ok=True)
    cli_enabled = use_cli and _env_flag("AD_CONTROL_ALLURE_CLI", True)
    # Default single-file for CLI reports; set AD_CONTROL_ALLURE_SINGLE_FILE=0 to keep multi-file.
    use_single_file = _env_flag("AD_CONTROL_ALLURE_SINGLE_FILE", True) if single_file is None else bool(single_file)
    command = _resolve_allure_command() if cli_enabled else None
    generate_error = "Allure CLI generation disabled" if not cli_enabled else ""
    if command:
        try:
            argv = [*command, "generate", str(source), "-o", str(target), "--clean"]
            if use_single_file:
                argv.append("--single-file")
            completed = subprocess.run(
                argv,
                check=False,
                capture_output=True,
                text=True,
            )
            if completed.returncode != 0:
                generate_error = (completed.stderr or completed.stdout or f"exit {completed.returncode}").strip()
                # Older Allure builds may not support --single-file; retry without it.
                if use_single_file and "single-file" in generate_error.lower():
                    completed = subprocess.run(
                        [*command, "generate", str(source), "-o", str(target), "--clean"],
                        check=False,
                        capture_output=True,
                        text=True,
                    )
                    if completed.returncode == 0:
                        generate_error = ""
                    else:
                        generate_error = (completed.stderr or completed.stdout or f"exit {completed.returncode}").strip()
        except (OSError, subprocess.SubprocessError) as exc:
            generate_error = str(exc)
    elif cli_enabled:
        generate_error = "Allure CLI was not found on PATH"
    index = target / "index.html"
    if not index.exists():
        if use_cli:
            detail = generate_error or "Allure generate did not produce index.html"
            index.write_text(
                "<!doctype html><html lang='zh-CN'><meta charset='utf-8'>"
                "<title>Allure report</title><body>"
                "<h1>Allure HTML 生成失败</h1>"
                "<p>请安装 Allure Commandline（及 Java），确保 Windows 上 <code>allure.bat</code> 在 PATH，"
                "然后重跑 <code>python scripts/generate_reports.py --run-dir ...</code>。</p>"
                f"<pre>{detail}</pre></body></html>",
                encoding="utf-8",
            )
        else:
            # Per-case stubs previously looked like empty Allure pages. Point to the
            # run-level report instead of writing a fake spinner page.
            index.write_text(
                "<!doctype html><html lang='zh-CN'><meta charset='utf-8'>"
                "<title>See run Allure report</title><body>"
                "<h1>单用例 Allure 页面未生成</h1>"
                "<p>请打开本次运行汇总报告：同 run 目录下的 "
                "<code>report/allure/index.html</code>，或读取 <code>report/allure-url.txt</code> "
                "里的 <code>http://127.0.0.1:...</code> 链接。</p>"
                "<p>重新生成并自动起本地服务：</p>"
                "<pre>python scripts/generate_reports.py --run-dir .artifacts/runs/&lt;run_id&gt;</pre>"
                "</body></html>",
                encoding="utf-8",
            )
    return index


def write_run_summary_markdown(
    run_dir: Path,
    case_results: list[dict[str, Any]],
    *,
    allure_url: str = "",
) -> Path:
    report_dir = run_dir / "report"
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / "summary.md"
    passed = sum(1 for item in case_results if item.get("status") in {"passed", "dry-run"})
    failed = len(case_results) - passed
    allure_path = run_dir / "report" / "allure" / "index.html"
    lines = [
        f"# Ad Control Run Summary: `{run_dir.name}`",
        "",
        f"- Cases/modes: **{len(case_results)}**",
        f"- Passed: **{passed}**",
        f"- Failed: **{failed}**",
        f"- Aggregated Allure file: `{allure_path}`",
    ]
    if allure_url:
        lines.append(f"- Aggregated Allure URL: {allure_url}")
    lines.extend(
        [
            "",
            "| Case | Mode | Status | Rule ID | Steps |",
            "|---|---|---|---|---|",
        ]
    )
    for item in case_results:
        step_names = " → ".join(str(step.get("name") or "step") for step in item.get("steps") or [])
        lines.append(
            f"| `{item.get('case_id')}` | `{item.get('mode')}` | `{item.get('status')}` | "
            f"`{item.get('rule_id') or '-'}` | {step_names or '-'} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def generate_run_allure_report(
    run_dir: str | Path,
    *,
    serve: bool | None = None,
    open_browser: bool | None = None,
) -> dict[str, Path | str]:
    """Aggregate every case/mode under a run into one Allure HTML report."""
    root = Path(run_dir).resolve()
    runs_root = (artifact_root() / "runs").resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f"run directory does not exist: {root}")
    if root.parent != runs_root:
        raise ValueError(f"run directory must be an immediate child of {runs_root}")

    case_results: list[dict[str, Any]] = []
    for run_json in sorted(root.glob("*/*/run.json")):
        data = json.loads(run_json.read_text(encoding="utf-8-sig"))
        data["run_id"] = root.name
        store = CaseArtifactStore(data["case_id"], data["mode"], root.name, root=runs_root.parent)
        write_allure_result(store, data)
        write_markdown(store, data)
        # Per-case Allure HTML is intentionally lightweight. The expensive CLI
        # generation is done once for the aggregated run below.
        generate_allure_html(store, use_cli=False)
        case_results.append(data)

    aggregated_results = root / "allure-results"
    if aggregated_results.exists():
        shutil.rmtree(aggregated_results)
    aggregated_results.mkdir(parents=True, exist_ok=True)
    for result_dir in root.glob("*/*/allure-results"):
        for item in result_dir.iterdir():
            if item.is_file():
                target = aggregated_results / item.name
                if target.exists():
                    target = aggregated_results / f"{item.stem}-{uuid.uuid4().hex[:8]}{item.suffix}"
                shutil.copy2(item, target)

    categories = [
        {
            "name": "流程失败",
            "matchedStatuses": ["failed"],
            "messageRegex": ".*",
        },
        {
            "name": "清理失败",
            "matchedStatuses": ["failed", "broken"],
            "traceRegex": ".*cleanup.*",
        },
    ]
    (aggregated_results / "categories.json").write_text(
        json.dumps(categories, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    environment = [
        f"run_id={root.name}",
        f"cases={len(case_results)}",
        f"passed={sum(1 for item in case_results if item.get('status') in {'passed', 'dry-run'})}",
        f"failed={sum(1 for item in case_results if item.get('status') not in {'passed', 'dry-run'})}",
    ]
    (aggregated_results / "environment.properties").write_text("\n".join(environment) + "\n", encoding="utf-8")

    aggregated_html = generate_allure_html(
        results_dir=aggregated_results,
        report_dir=root / "report" / "allure",
        use_cli=True,
    )
    published = publish_allure_report(aggregated_html, serve=serve, open_browser=open_browser)
    summary = write_run_summary_markdown(root, case_results, allure_url=str(published.get("allure_url") or ""))
    return {
        "allure_html": aggregated_html,
        "allure_url": published.get("allure_url") or "",
        "summary_markdown": summary,
        "allure_results": aggregated_results,
    }


def regenerate_run_reports(
    run_dir: str | Path,
    *,
    serve: bool | None = None,
    open_browser: bool | None = None,
) -> list[Path | str]:
    outputs = generate_run_allure_report(run_dir, serve=serve, open_browser=open_browser)
    paths: list[Path | str] = [outputs["allure_html"], outputs["summary_markdown"]]
    if outputs.get("allure_url"):
        paths.append(str(outputs["allure_url"]))
    return paths
