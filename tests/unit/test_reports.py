from __future__ import annotations

import json
from pathlib import Path

from ad_control.artifact_store import CaseArtifactStore
from ad_control.report_generator import (
    generate_allure_html,
    generate_run_allure_report,
    write_allure_result,
    write_markdown,
)


def test_reports_are_created() -> None:
    root = Path(".artifacts/test-fixtures/reports")
    root.mkdir(parents=True, exist_ok=True)
    store = CaseArtifactStore("case", "hit", "run", root)
    store.write_json(
        "validation-result.json",
        {"status": "failed", "matched": False, "match_count": 0, "error": "no log"},
    )
    store.write_json(
        "seed-plan.json",
        {
            "table": "demo_table",
            "channel_code": "demo-channel",
            "row_strategy": "copy-then-patch",
            "rows": [{"project_id": "1"}],
            "conditions": [
                {
                    "column": "consume",
                    "compare_type": "ge",
                    "val1": 10,
                    "effective_mode": "hit",
                }
            ],
        },
    )
    result = {
        "case_id": "case",
        "name": "Case",
        "mode": "hit",
        "run_id": "run",
        "status": "failed",
        "cleanup_status": "passed",
        "error": "bad",
        "steps": [
            {"name": "创建广告管控规则", "status": "passed"},
            {"name": "生成并写入 HIT 测试数据", "status": "passed", "table": "demo_table", "channel_code": "demo-channel"},
            {"name": "校验 HIT 管控结果", "status": "failed", "match_count": 0, "message": "no log"},
        ],
        "artifacts": {},
    }
    allure_result = write_allure_result(store, result)
    markdown = write_markdown(store, result)
    html = generate_allure_html(store)
    assert allure_result.exists() and markdown.exists() and html.exists()
    assert "Case" in markdown.read_text(encoding="utf-8")
    payload = json.loads(allure_result.read_text(encoding="utf-8"))
    assert payload["status"] == "failed"
    assert payload["steps"]
    assert any(step.get("statusDetails", {}).get("message") for step in payload["steps"])
    assert payload["attachments"]
    assert "Flow" in payload["description"]


def test_run_level_report_aggregates_modes() -> None:
    root = Path(".artifacts/test-fixtures/run-agg-root")
    if root.exists():
        import shutil

        shutil.rmtree(root)
    runs = root / "runs" / "run-agg"
    for mode in ("hit", "miss"):
        store = CaseArtifactStore("demo-case", mode, "run-agg", root=root)
        store.write_json(
            "validation-result.json",
            {"status": "passed", "matched": mode == "hit", "match_count": int(mode == "hit")},
        )
        store.write_json("seed-plan.json", {"table": "t", "rows": [], "conditions": []})
        payload = {
            "case_id": "demo-case",
            "name": "Demo",
            "mode": mode,
            "run_id": "run-agg",
            "status": "passed",
            "rule_id": f"r-{mode}",
            "cleanup_status": "passed",
            "steps": [
                {"name": "创建广告管控规则", "status": "passed"},
                {"name": f"校验 {mode.upper()} 管控结果", "status": "passed", "matched": mode == "hit"},
            ],
            "started_at": "2026-09-04T07:20:42.099010+00:00",
            "finished_at": "2026-09-04T07:20:45.717087+00:00",
            "artifacts": {},
        }
        store.write_json("run.json", payload)
        write_allure_result(store, payload)
        write_markdown(store, payload)
        generate_allure_html(store)

    # generate_run_allure_report only accepts children of project .artifacts/runs,
    # so place a mirror under the real runs tree for aggregation.
    real_run = Path(".artifacts/runs/_test_run_agg")
    if real_run.exists():
        import shutil

        shutil.rmtree(real_run)
    import shutil

    shutil.copytree(runs, real_run)
    outputs = generate_run_allure_report(real_run, serve=False, open_browser=False)
    assert outputs["allure_html"].exists()
    assert outputs["summary_markdown"].exists()
    assert outputs.get("allure_url") == ""
    summary = outputs["summary_markdown"].read_text(encoding="utf-8")
    assert "demo-case" in summary
    assert "`hit`" in summary and "`miss`" in summary
    result_files = list(outputs["allure_results"].glob("*-result.json"))
    assert len(result_files) >= 2


def test_serve_report_directory_returns_http_url(tmp_path: Path) -> None:
    from urllib.request import urlopen

    from ad_control.report_generator import serve_report_directory

    report_dir = tmp_path / "allure"
    report_dir.mkdir()
    (report_dir / "index.html").write_text("<html><body>ok</body></html>", encoding="utf-8")
    url = serve_report_directory(report_dir, open_browser=False)
    assert url.startswith("http://127.0.0.1:")
    assert url.endswith("/index.html")
    with urlopen(url, timeout=5) as response:  # noqa: S310 - localhost only
        body = response.read().decode("utf-8")
    assert "ok" in body
    assert (tmp_path / "allure-url.txt").read_text(encoding="utf-8").strip() == url


def test_start_detached_report_server_survives_caller(tmp_path: Path) -> None:
    from urllib.request import urlopen

    from ad_control.report_generator import start_detached_report_server

    report_dir = tmp_path / "allure"
    report_dir.mkdir()
    (report_dir / "index.html").write_text("<html><body>detached-ok</body></html>", encoding="utf-8")
    url = start_detached_report_server(report_dir, open_browser=False)
    assert url.startswith("http://127.0.0.1:")
    with urlopen(url, timeout=5) as response:  # noqa: S310 - localhost only
        body = response.read().decode("utf-8")
    assert "detached-ok" in body
    assert (tmp_path / "allure-url.txt").read_text(encoding="utf-8").strip() == url
    pid_file = tmp_path / "allure-server.pid"
    assert pid_file.exists()
