"""Serve an Allure report directory until Ctrl+C / process kill.

Intended as a long-lived process so REPORT_URL stays reachable after parent CLIs exit.
"""

from __future__ import annotations

import argparse
import os
import threading
from pathlib import Path

from _bootstrap import ROOT  # noqa: F401
from ad_control.report_generator import serve_report_directory


def main() -> int:
    parser = argparse.ArgumentParser(description="Keep serving an Allure report over HTTP")
    parser.add_argument("--report-dir", required=True, help="directory that contains index.html")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--no-open", action="store_true")
    parser.add_argument("--pid-file", default="", help="optional path to write this process pid")
    args = parser.parse_args()

    report_dir = Path(args.report_dir)
    if not report_dir.is_absolute():
        report_dir = ROOT / report_dir
    if args.pid_file:
        Path(args.pid_file).write_text(f"{os.getpid()}\n", encoding="utf-8")

    url = serve_report_directory(
        report_dir,
        host=args.host,
        port=args.port or None,
        open_browser=not args.no_open,
    )
    print(f"REPORT_URL={url}", flush=True)
    print("Serving until Ctrl+C ...", flush=True)
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        print("stopped", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
