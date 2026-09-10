"""Pytest defaults for this repository.

The execution environment may deny access to the user's system pytest temp
folder. Keep pytest's temporary directories under the repository artifact
area, just like runtime reports and other generated files.
"""
from __future__ import annotations

import os
from pathlib import Path


def pytest_configure(config) -> None:
    """Use repository-local temp files and skip JVM-backed Allure in tests."""
    if config.option.basetemp is None:
        config.option.basetemp = str(
            Path(config.rootpath) / ".artifacts" / "state" / "pytest-tmp"
        )
    # Unit/integration tests only need the generated Allure result files.
    # Starting the JVM-backed CLI for every report makes the suite needlessly slow.
    os.environ.setdefault("AD_CONTROL_ALLURE_CLI", "0")
    # Do not bind HTTP ports or open browsers during unit tests.
    os.environ.setdefault("AD_CONTROL_ALLURE_SERVE", "0")
    os.environ.setdefault("AD_CONTROL_ALLURE_OPEN_BROWSER", "0")
    os.environ.setdefault("AD_CONTROL_ALLURE_DETACH", "0")
