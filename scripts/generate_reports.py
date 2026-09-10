from __future__ import annotations

import argparse

from _bootstrap import ROOT  # noqa: F401
from ad_control.report_generator import regenerate_run_reports


def main() -> int:
    parser = argparse.ArgumentParser(
        description="重新生成已有 run 的 Allure HTML / Markdown，并默认起本地 HTTP 给出可打开链接"
    )
    parser.add_argument("--run-dir", required=True)
    parser.add_argument(
        "--no-serve",
        action="store_true",
        help="只生成文件，不起本地 HTTP、不打开浏览器",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="起本地 HTTP 但不自动打开浏览器",
    )
    args = parser.parse_args()
    serve = not args.no_serve
    open_browser = serve and not args.no_open
    for path in regenerate_run_reports(args.run_dir, serve=serve, open_browser=open_browser):
        text = str(path)
        if text.startswith("http://") or text.startswith("https://"):
            print(f"REPORT_URL={text}")
        else:
            print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
