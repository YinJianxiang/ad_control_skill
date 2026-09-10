from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .redaction import redact


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def artifact_root(root: Path | None = None) -> Path:
    project_artifacts = (project_root() / ".artifacts").resolve()
    if root is not None:
        candidate = Path(root).resolve()
    else:
        configured = Path(os.getenv("AD_CONTROL_ARTIFACT_ROOT", ".artifacts"))
        candidate = configured.resolve() if configured.is_absolute() else (project_root() / configured).resolve()
    if candidate != project_artifacts and project_artifacts not in candidate.parents:
        raise ValueError(f"artifact root must stay under the project .artifacts directory: {candidate}")
    return candidate


def new_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", str(value)).strip("-") or "case"


def strict_run_id(value: str) -> str:
    text = str(value).strip()
    if not text or text in {".", ".."} or safe_name(text) != text:
        raise ValueError("run_id may contain only letters, numbers, dot, underscore, and hyphen")
    return text


class CaseArtifactStore:
    def __init__(self, case_id: str, mode: str, run_id: str | None = None, root: Path | None = None):
        self.run_id = strict_run_id(run_id or new_run_id())
        self.case_id = safe_name(case_id)
        self.mode = safe_name(mode)
        # Keep the containment check lexical here. Resolving a not-yet-created
        # sibling path on Windows can race when HIT and MISS for one case are
        # initialized concurrently and incorrectly resolve outside runs_root.
        runs_root = (artifact_root(root) / "runs").absolute()
        candidate = (runs_root / self.run_id / self.case_id / self.mode).absolute()
        if runs_root not in candidate.parents:
            raise ValueError("case artifact path escaped .artifacts/runs")
        self.root = candidate
        self.allure_results = self.root / "allure-results"
        self.report_dir = self.root / "report"
        self.allure_report = self.report_dir / "allure"
        for directory in (self.root, self.allure_results, self.report_dir):
            directory.mkdir(parents=True, exist_ok=True)

    def path(self, filename: str) -> Path:
        candidate = (self.root / filename).resolve()
        if self.root.resolve() not in candidate.parents and candidate != self.root.resolve():
            raise ValueError(f"artifact path must stay inside the case directory: {filename}")
        candidate.parent.mkdir(parents=True, exist_ok=True)
        return candidate

    def write_json(self, filename: str, value: Any, sensitive: bool = True) -> Path:
        path = self.path(filename)
        data = redact(value) if sensitive else value
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
        return path

    def write_text(self, filename: str, text: str) -> Path:
        path = self.path(filename)
        path.write_text(text, encoding="utf-8")
        return path
