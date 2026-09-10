---
name: ad-control-report
description: "从 .artifacts/runs 下已有运行产物，为每个用例与模式重新生成脱敏 Markdown 报告与 Allure HTML 报告。用于在不重跑业务动作的情况下恢复或审阅报告。"
---

## 适用场景

运行产物已存在、需要重新生成报告时使用。

## 前置条件

运行目录必须是 `.artifacts/runs` 的直接子目录。报告生成不调用 API 或数据库。

## 输入

`.artifacts/runs/<run_id>`

## 命令

```powershell
python scripts\generate_reports.py --run-dir .artifacts\runs\<run_id>
python scripts\open_allure_report.py --run-dir .artifacts\runs\<run_id>
```

`generate_reports.py` 默认会：

1. 用 Allure CLI `--single-file` 生成汇总 HTML
2. 在本机起 HTTP 服务
3. 打印并可点击打开 `REPORT_URL=http://127.0.0.1:<port>/index.html`
4. 把同一 URL 写入 `.artifacts/runs/<run_id>/report/allure-url.txt`

只要文件、不要服务时加 `--no-serve`；只要服务不要弹浏览器时加 `--no-open`。

## 输出

- 每个用例/模式：`report/case.md`、`allure-results/*`（单用例页面仅提示去看汇总报告）
- 整次运行汇总：`.artifacts/runs/<run_id>/report/summary.md`、`report/allure/index.html`、`report/allure-url.txt`
- 控制台：`REPORT_URL=http://127.0.0.1:.../index.html`

请优先用 `REPORT_URL` / `allure-url.txt`，不要直接双击一堆分散的 `file://` HTML（多文件 Allure 在浏览器里会空白转圈）。

## 安全门禁

对嵌套值与自由文本中的密钥脱敏。Allure CLI/Java 仅允许用于生成 HTML。本地 HTTP 默认只绑 `127.0.0.1`。所有文件保留在运行目录内。

环境变量：

- `AD_CONTROL_ALLURE_SERVE=0`：不起 HTTP
- `AD_CONTROL_ALLURE_OPEN_BROWSER=0`：不起浏览器
- `AD_CONTROL_ALLURE_DETACH=0`：不用独立进程常驻（默认独立进程，CLI 退出后链接仍可用）
- `AD_CONTROL_ALLURE_SINGLE_FILE=0`：退回多文件 Allure（仍建议走 HTTP）

## 失败处理

当 Allure CLI 不可用时，保留有效的原始 result JSON，并生成可读的降级 HTML 页面。

## 禁止事项

禁止从任意外部目录重新生成、包含凭证，或在报告恢复过程中执行业务流程。
