"""Open an existing run Allure report via a durable localhost HTTP URL."""

from __future__ import annotations

import argparse
from pathlib import Path

from _bootstrap import ROOT  # noqa: F401
from ad_control.report_generator import publish_allure_report, regenerate_run_reports, serve_report_directory
import threading


def main() -> int:
    parser = argparse.ArgumentParser(description="用 localhost HTTP 打开已有 Allure 报告")
    parser.add_argument("--run-dir", required=True, help=".artifacts/runs/<run_id>")
    parser.add_argument("--regenerate", action="store_true", help="先重新生成再打开")
    parser.add_argument("--no-open", action="store_true", help="只打印 URL，不打开浏览器")
    parser.add_argument(
        "--foreground",
        action="store_true",
        help="前台常驻（Ctrl+C 结束）；默认后台独立进程，关掉本命令后链接仍可用",
    )
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    if not run_dir.is_absolute():
        run_dir = ROOT / run_dir

    if args.regenerate:
        outputs = regenerate_run_reports(
            run_dir,
            serve=True,
            open_browser=not args.no_open,
        )
        url = str(outputs.get("allure_url") or "")
        if not url:
            for item in outputs.values():
                text = str(item)
                if text.startswith("http://") or text.startswith("https://"):
                    url = text
                    break
        if not url:
            print("no report URL produced")
            return 1
        print(f"REPORT_URL={url}")
        if args.foreground:
            print("Serving in foreground until Ctrl+C ...")
            try:
                threading.Event().wait()
            except KeyboardInterrupt:
                print("stopped")
        return 0

    index = run_dir / "report" / "allure" / "index.html"
    if not index.exists():
        print(f"missing report: {index}; retry with --regenerate")
        return 1

    if args.foreground:
        url = serve_report_directory(index.parent, open_browser=not args.no_open)
        print(f"REPORT_URL={url}")
        print("Serving in foreground until Ctrl+C ...")
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            print("stopped")
        return 0

    published = publish_allure_report(
        index,
        serve=True,
        open_browser=not args.no_open,
        detach=True,
    )
    url = published.get("allure_url") or ""
    if not url:
        print(f"failed to serve {index}")
        return 1
    print(f"REPORT_URL={url}")
    print("server detached; link stays up until you kill the serve process")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
