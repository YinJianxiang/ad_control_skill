---
name: ad-control-knowledge
description: 广告管控自动化所需的前端指标矩阵、后端字段、公式、数据表结构和授权知识。
---

## 适用场景

当需要确认某条业务线在规则页面可选择哪些指标，或判断指标是否具备后端公式、数据表和单指标造数能力时使用。

## 知识库结构

- 前端指标矩阵：`configs/knowledge/frontend-metric-matrix/<业务线编码>.json`
- 授权与造数知识：`.cursor/skills/ad-control-knowledge/authorized-scenarios.json`
- 业务线正式说明：`.cursor/skills/ad-control-knowledge/knowledge/业务线/<业务线>（<编码>）.md`
- 单书/剧数据筛选造数（通用）：`.cursor/skills/ad-control-knowledge/knowledge/单书剧数据筛选-造数规则.md`
- 规则范围过滤造数（通用）：`.cursor/skills/ad-control-knowledge/knowledge/规则范围过滤-造数约束.md`

主表造数除指标阈值外，必须按「规则范围过滤」知识让行通过 Job WHERE（负责人、剧类型、主体、状态等）及小时窗口（`nearlyNHour`）；该知识跨业务线、跨用例，不绑定具体 case。

规则开启「单书/剧数据筛选」时，除管控条件主表造数外，必须按单书剧通用规则补**书剧大盘（渠道日表按 book_id）**；该知识跨业务线、跨用例，不绑定具体 case。

当前已整理的业务线：

- 客户端-付费小说（`cltmain`）
- 新媒体-短剧（`xmtplay`）
- 客户端-免费短剧（`syhplay`）
- 新媒体-短篇（`cpsshort`）
- 新媒体-免费短剧（`cpsvideomf`）
- 新媒体-免费小说（`cpsfree`）
- 客户端-付费短剧（`cltplay`）
- 头条端原生-免费（`cpsdyfree`）
- 头条端原生-付费（`cpsdy`）

## 正式业务线文件内容

每条业务线文件统一整理：

1. 数据表映射、时间粒度、分组字段和聚合方式。
2. 指标编码、指标类型、完整公式和时间口径。
3. 造数字段、求和/比率聚合规则及当前状态。
4. 前端时间范围、聚合条件和可选指标数量。
5. 单指标授权、验证和待补充项处理流程。

## 重要边界

- 前端矩阵表示页面可选项，不等于后端现行公式或可执行造数能力。
- `backendMetricCode` 为空时，不能直接用于造数或执行规则。
- 当前授权白名单为空；只有未来完成公式、表字段和验证闭环的指标，才能重新进入授权白名单。
- `待补充` 或 `FORMULA_UNSUPPORTED` 只能表示待复核，不能解释为没有指标。
- 比率类指标必须先分别聚合分子和分母，再计算并按公式舍入。
- 日口径使用 `D0`、`D1`、`RDn_BEGIN`/`RDn_END` 等时间标签；小时口径使用 `Hn`。
- `consume` 与 `hour_consume` 是不同时间粒度的指标编码，不能混用。

## 整理与校验

```powershell
python scripts\import_frontend_metric_matrix.py
python scripts\validate_frontend_metric_matrix.py
python scripts\rebuild_business_formula_docs.py
```

原始采集文件只能放在 `.artifacts/runs/` 下。当前整理结果仅保留待复核的候选表、字段、公式、时间口径、聚合方式和状态；不代表已确认、已授权或可执行。

## 执行前检查

1. 确认业务线编码、维度、投放版本、时间范围和聚合条件一致。
2. 从对应业务线正式文件读取指标、表映射、公式和造数字段。
3. 使用 `backendMetricCode` 与授权知识交叉检查。
4. 公式或字段不明确时返回 `FORMULA_UNSUPPORTED`，禁止猜测并写入知识库。
5. 涉及测试数据库的写入或删除，必须使用 `AD_CONTROL_DB_ENV=test`。
