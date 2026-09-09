---
name: ad-control-seed-data
description: "从 JSON 用例编译已授权、感知聚合的 HIT/MISS 造数行，可选事务性写入 MySQL 测试库，并生成精确的基于文件的清理清单。用于造数预览、执行或清理恢复。"
---

## 适用场景

仅预览或执行造数阶段时使用。

## 前置条件

精确的业务线、维度、发布版本、时间类型、归约类型、指标、表、字段与公式必须已在 `authorized-scenarios.json` 中授权。在 `--execute` 之前，展示用例、模式、规则 ID、表、DB 主机/库名、行数、清理谓词与产物路径；请用户明确确认。

主表造数必须同时满足指标阈值与规则范围过滤（负责人、剧类型、主体、状态、小时窗口等），按通用知识推导，禁止按单个 case 特例硬编码：

`.cursor/skills/ad-control-knowledge/knowledge/规则范围过滤-造数约束.md`

若规则开启「单书/剧数据筛选」，除主表 HIT/MISS 外，还必须按通用知识补书剧大盘造数与清理：

`.cursor/skills/ad-control-knowledge/knowledge/单书剧数据筛选-造数规则.md`

## 输入

- 用例 JSON
- `--mode hit|miss`
- 写入用的动态 `rule_id`
- 测试库环境

## 命令

```powershell
python scripts\seed_data.py --case configs\cases\<case>.json --mode hit
python scripts\seed_data.py --case configs\cases\<case>.json --mode miss
python scripts\seed_data.py --case configs\cases\<case>.json --mode hit --execute --rule-id <rule_id>
```

清理恢复预览与执行：

```powershell
python scripts\cleanup_seed.py --manifest .artifacts\runs\<run_id>\<case_id>\<mode>\cleanup-manifest.json
python scripts\cleanup_seed.py --manifest .artifacts\runs\<run_id>\<case_id>\<mode>\cleanup-manifest.json --execute
```

## 输出

`seed-plan.json`、`seed-audit.json`、`cleanup-manifest.json` 与 `SeedHandoff`。清单在插入前写为 `planned`，提交后更新。

## 安全门禁

写入/删除要求 `AD_CONTROL_DB_ENV=test`。未知字段或场景在 SQL 前失败。清理使用已持久化的谓词，禁止重新计算范围。

## 失败处理

插入失败则回滚。若提交后产物持久化失败，尝试补偿清理；若补偿也失败，同时报告两类错误。

## 禁止事项

禁止臆造表列、添加未核验的标记列、使用生产库、自动授权探查知识，或在清单谓词为空时删除。
