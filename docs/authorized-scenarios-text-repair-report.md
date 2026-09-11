# authorized-scenarios.json 文本占位符修复报告

- 生成时间：`2026-09-11T17:30:16+08:00`
- 模式：`execute`
- 源文件：`D:\Project\ad_control_skill\.cursor\skills\ad-control-knowledge\authorized-scenarios.json`
- 修复前 SHA-256：`4e44d97a973541711b357b1294f580a756def3d91007f8513342ea2a40ea643d`
- 修复后 SHA-256：`9365c75b75951e8910d637e31f843ad0224f5bc70ec01e0bbff999237142672d`
- 指标记录变更：`75`
- UI scope 记录变更：`1`
- 替换的问号占位值：`79`
- 未解决项：`0`
- 剩余占位符：`0`
- 执行前备份：`D:\Project\ad_control_skill\.artifacts\knowledge-repair\20260911-173016\authorized-scenarios.json`

## 修复原则

1. 已有正常别名优先，只删除同一记录中的问号占位符。
2. 缺少正常别名时，仅使用前端指标矩阵和接口指标映射中的现有名称。
3. 多个来源给出不同但有效的 UI 名称时全部保留，不猜测唯一名称。
4. UI scope 展示名必须按业务线、维度、投放版本、时间和聚合条件精确匹配矩阵。

## 指标别名变更

| JSON 路径 | column | 删除 | 写入 |
|---|---|---|---|
| `$.metrics[68].uiAliases` | `consume` | `??` | `分日消耗, 当日消耗, 消耗` |
| `$.metrics[70].uiAliases` | `active_cost` | `????` | `激活成本` |
| `$.metrics[71].uiAliases` | `pay_cost` | `????` | `付费成本` |
| `$.metrics[72].uiAliases` | `n_recharge_uv` | `??UV` | `充值UV` |
| `$.metrics[73].uiAliases` | `n_recharge_amount` | `????` | `充值金额` |
| `$.metrics[74].uiAliases` | `unsubscribe_rate` | `???` | `当日退订率` |
| `$.metrics[75].uiAliases` | `convert_cost` | `????` | `转化成本` |
| `$.metrics[76].uiAliases` | `conversion_subscribe_rate` | `???` | `转订率` |
| `$.metrics[77].uiAliases` | `ac_rate` | `????` | `拉活占比` |
| `$.metrics[78].uiAliases` | `bid_rate` | `???` | `计费比, 转化计费比` |
| `$.metrics[79].uiAliases` | `predict_roi` | `??ROI` | `当日的预估ROI` |
| `$.metrics[80].uiAliases` | `hour_consume` | `????` | `分时消耗` |
| `$.metrics[81].uiAliases` | `hour_n_recharge_uv` | `????UV` | `分时充值UV` |
| `$.metrics[82].uiAliases` | `hour_active_cost` | `??????` | `分时激活成本` |
| `$.metrics[83].uiAliases` | `hour_pay_cost` | `??????` | `分时付费成本` |
| `$.metrics[84].uiAliases` | `hour_unsubscribe_rate` | `?????` | `分时退订率` |
| `$.metrics[85].uiAliases` | `hour_convert_cost` | `??????` | `分时转化成本` |
| `$.metrics[86].uiAliases` | `hour_conversion_subscribe_rate` | `?????` | `分时转订率` |
| `$.metrics[87].uiAliases` | `hour_ac_rate` | `??????` | `分时拉活占比` |
| `$.metrics[88].uiAliases` | `hour_bid_rate` | `?????` | `分时计费比` |
| `$.metrics[89].uiAliases` | `hour_predict_roi` | `????ROI` | `分时预估ROI` |
| `$.metrics[91].uiAliases` | `active_cost` | `????` | `激活成本` |
| `$.metrics[92].uiAliases` | `pay_cost` | `????` | `付费成本, 当日付费成本` |
| `$.metrics[93].uiAliases` | `n_recharge_uv` | `??UV` | `充值UV` |
| `$.metrics[94].uiAliases` | `n_recharge_amount` | `????` | `充值金额` |
| `$.metrics[95].uiAliases` | `unsubscribe_rate` | `???` | `分日退订率, 当日退订率, 退订率` |
| `$.metrics[96].uiAliases` | `convert_cost` | `????` | `转化成本` |
| `$.metrics[97].uiAliases` | `conversion_subscribe_rate` | `???` | `转订率` |
| `$.metrics[98].uiAliases` | `ac_rate` | `????` | `拉活占比` |
| `$.metrics[99].uiAliases` | `bid_rate` | `???` | `计费比` |
| `$.metrics[100].uiAliases` | `predict_roi` | `??ROI` | `分日预估ROI, 当日的预估ROI, 预估ROI` |
| `$.metrics[101].uiAliases` | `hour_consume` | `????` | `分时消耗` |
| `$.metrics[102].uiAliases` | `hour_n_recharge_uv` | `????UV` | `分时充值UV` |
| `$.metrics[103].uiAliases` | `hour_active_cost` | `??????` | `分时激活成本` |
| `$.metrics[104].uiAliases` | `hour_pay_cost` | `??????` | `分时付费成本` |
| `$.metrics[105].uiAliases` | `hour_unsubscribe_rate` | `?????` | `分时退订率` |
| `$.metrics[106].uiAliases` | `hour_convert_cost` | `??????` | `分时转化成本` |
| `$.metrics[107].uiAliases` | `hour_conversion_subscribe_rate` | `?????` | `分时转订率` |
| `$.metrics[108].uiAliases` | `hour_ac_rate` | `??????` | `分时拉活占比` |
| `$.metrics[109].uiAliases` | `hour_bid_rate` | `?????` | `分时计费比` |
| `$.metrics[110].uiAliases` | `hour_predict_roi` | `????ROI` | `分时预估ROI` |
| `$.metrics[111].uiAliases` | `hour_convert_num` | `?????` | `分时转化数` |
| `$.metrics[112].uiAliases` | `hour_unsubscribe_rate` | `?????` | `分时退订率` |
| `$.metrics[113].uiAliases` | `cost_diff` | `????` | `成本差值` |
| `$.metrics[114].uiAliases` | `pline_form_roi` | `???ROI` | `分线ROI` |
| `$.metrics[115].uiAliases` | `all_stat_total_cost_trend` | `????` | `全域成本` |
| `$.metrics[116].uiAliases` | `all_roi_trend` | `??ROI` | `全域ROI` |
| `$.metrics[117].uiAliases` | `all_roi_24h_trend` | `??24??ROI` | `全域24小时ROI` |
| `$.metrics[118].uiAliases` | `hour_all_stat_total_cost_trend` | `??????` | `分时全域成本` |
| `$.metrics[119].uiAliases` | `hour_all_roi_trend` | `????ROI` | `分时全域ROI` |
| `$.metrics[120].uiAliases` | `hour_all_roi_24h_trend` | `????24??ROI` | `分时全域24小时ROI` |
| `$.metrics[121].uiAliases` | `convert_cost` | `????` | `分日转化成本, 转化成本` |
| `$.metrics[124].uiAliases` | `hour_roi_h2` | `??ROI_H2` | `分时ROI_H2` |
| `$.metrics[126].uiAliases` | `hour_roi_h3` | `??ROI_H3` | `分时ROI_H3` |
| `$.metrics[127].uiAliases` | `hour_roi_h4` | `??ROI_H4` | `分时ROI_H4` |
| `$.metrics[129].uiAliases` | `hour_roi_h12` | `??ROI_H12` | `分时ROI_H12` |
| `$.metrics[130].uiAliases` | `hour_convert_num` | `?????` | `分时转化数` |
| `$.metrics[131].uiAliases` | `hour_bid_rate` | `?????` | `分时计费比, 分时转化计费比` |
| `$.metrics[132].uiAliases` | `hour_convert_cost` | `??????` | `分时转化成本` |
| `$.metrics[133].uiAliases` | `pline_form_roi` | `???ROI` | `分线ROI` |
| `$.metrics[134].uiAliases` | `all_stat_total_cost_trend` | `????` | `全域成本` |
| `$.metrics[135].uiAliases` | `all_roi_trend` | `??ROI` | `全域ROI` |
| `$.metrics[136].uiAliases` | `all_roi_24h_trend` | `??24??ROI` | `全域24小时ROI` |
| `$.metrics[137].uiAliases` | `hour_all_stat_total_cost_trend` | `??????` | `分时全域成本` |
| `$.metrics[138].uiAliases` | `hour_all_roi_trend` | `????ROI` | `分时全域ROI` |
| `$.metrics[139].uiAliases` | `hour_all_roi_24h_trend` | `????24??ROI` | `分时全域24小时ROI` |
| `$.metrics[140].uiAliases` | `pline_form_roi` | `???ROI` | `分线ROI` |
| `$.metrics[141].uiAliases` | `pline_form_roi` | `???ROI` | `分线ROI` |
| `$.metrics[142].uiAliases` | `hour_micro_game_0d_roi` | `??????ROI` | `分时广告变现ROI` |
| `$.metrics[143].uiAliases` | `hour_convert_num` | `?????` | `分时转化数` |
| `$.metrics[144].uiAliases` | `pline_form_roi` | `???ROI` | `分线ROI` |
| `$.metrics[145].uiAliases` | `hour_all_stat_total_cost_trend` | `??????` | `分时全域成本` |
| `$.metrics[146].uiAliases` | `hour_convert_num` | `?????` | `分时转化数` |
| `$.metrics[148].uiAliases` | `pline_form_roi` | `???ROI` | `分线ROI` |
| `$.metrics[149].uiAliases` | `hour_all_stat_total_cost_trend` | `??????` | `分时全域成本` |

## UI scope 变更

| JSON 路径 | key | 写入 |
|---|---|---|
| `$.uiMetricScopes[0]` | `cpsdyfree|promotion|auction|1|0|total` | `{"businessLineName": "头条端原生-免费", "dimensionName": "广告", "timeName": "当天", "reduceName": "累计"}` |
