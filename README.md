# 广告管控 Skill

## 1. 项目定位

本项目是一个纯 Python 的广告管控规则验证项目，使用真实的规则 API、规则执行服务和测试 MySQL 完成端到端验证。

正式流程不打开业务页面，不使用 Playwright、browser-use、TypeScript 或 Node.js 执行业务逻辑，也不连接生产数据库。

完整链路如下：

~~~text
JSON 用例
  → 读取指标知识与授权知识
  → 创建广告管控规则
  → 生成 HIT/MISS 测试数据
  → 写入测试 MySQL
  → 触发规则执行服务
  → 查询结果记录校验 HIT/MISS
  → 清理测试数据
  → 生成 Markdown 和 Allure 报告
~~~

每个用例通常分别运行 hit 和 miss 两种模式，除非用例通过 modes 明确限制模式。

---

## 2. Skill 的职责和串联关系

项目中的 Skill 文档用于说明流程约束和业务口径；当前证据已清理，执行前必须重新确认接口、数据表、字段和规则参数。

| Skill | 作用 | 流程位置 |
|---|---|---|
| ad-control-knowledge | 保存前端指标矩阵、后端指标 code、公式、数据表、字段、造数策略和授权状态，决定指标是否允许执行。 | 所有流程的基础和前置校验 |
| ad-control-api-create | 根据用例构建、校验并提交规则创建 API 请求，提取唯一动态 rule_id。 | 第一步：创建规则 |
| ad-control-seed-data | 根据授权知识编译 HIT/MISS 造数计划，必要时写入测试 MySQL，并生成清理清单。 | 第二步：准备测试数据 |
| ad-control-result-validation | 使用 rule_id、channel_code 和维度触发 规则执行服务，并轮询 ad_data_control_log 校验 HIT 或 MISS。 | 第三步：触发 规则执行服务 并验证 |
| ad-control-report | 从已有运行产物重新生成 Markdown 和 Allure HTML，不重新调用 API 或数据库。 | 最后一步：生成或恢复报告 |
| ad-control-api-flow | 编排规则创建、造数、规则执行服务、校验、清理和报告，支持单用例、全量、串行和并行运行。 | 主流程编排器 |
| ad-control-empirical-auth | 对尚未授权的指标格子做测试环境闭环实测，只有观察到 HIT 才写入授权知识。 | 可选：扩充或修正知识库 |

### 2.1 Skill 串联图

~~~mermaid
flowchart TD
    K[ad-control-knowledge<br/>指标矩阵、公式、表字段、授权状态]
    C[JSON 用例<br/>configs/cases/*.json]
    F[ad-control-api-flow<br/>run_cases.py]
    A[ad-control-api-create<br/>创建规则并取得 rule_id]
    S[ad-control-seed-data<br/>编译并写入 HIT/MISS 测试数据]
    V[ad-control-result-validation<br/>触发 规则执行服务 并轮询 ad_data_control_log]
    X[清理测试数据<br/>cleanup manifest]
    R[ad-control-report<br/>Markdown + Allure]
    E[ad-control-empirical-auth<br/>可选实测授权]

    K --> C
    C --> F
    F --> A
    A --> S
    S --> V
    V --> X
    X --> R
    E --> K
~~~

### 2.2 可选的实测授权链路

当知识库中没有某个指标格子的授权记录时，不能臆造公式或字段。使用 ad-control-empirical-auth 做一次测试环境闭环：

~~~text
创建页元数据接口 /3231、/3232
  → 确认页面允许选择该指标
  → 创建测试规则
  → 生成并写入测试数据
  → 触发 规则执行服务
  → ad_data_control_log 出现 HIT
  → 才写入 authorized-scenarios.json
~~~

接口拒绝、没有有效造数配方或观察窗口内没有 HIT 时，不写入授权状态。

---

## 3. 目录和关键文件

~~~text
configs/
├─ cases/                              # JSON 规则验证用例
└─ knowledge/frontend-metric-matrix/   # 前端页面指标矩阵
docs/
├─ generated/business-metrics/         # 自动生成的业务线指标与公式文档
│  ├─ business-lines/                  # 各业务线指标、表映射、公式和状态
│  ├─ formula-catalog/                 # 候选待确认公式及时间变体目录
│  └─ summary/                         # 业务线汇总（Markdown/CSV/JSON）
└─ examples/indicator-authorization/   # 单指标授权示例

.cursor/skills/
├─ ad-control-knowledge/          # 授权知识库和业务知识
├─ ad-control-api-create/         # 规则创建
├─ ad-control-seed-data/          # 造数
├─ ad-control-result-validation/  # 规则执行服务 和数据库校验
├─ ad-control-report/             # 报告
├─ ad-control-api-flow/           # 完整流程编排
└─ ad-control-empirical-auth/     # 实测授权

scripts/
├─ run_cases.py                              # 完整流程入口
├─ run_cpsdy_channel_auction_today_batch.py # CPSDY 渠道竞价当天批量入口
├─ create_rule.py                            # 单独创建规则
├─ seed_data.py                              # 单独造数
├─ validate_result.py                        # 单独触发 规则执行服务 并校验
├─ cleanup_seed.py                           # 按清单清理测试数据
├─ generate_reports.py                       # 重新生成已有报告
├─ authorize_empirical.py                    # 实测授权
├─ validate_frontend_metric_matrix.py        # 校验前端指标矩阵
├─ rebuild_business_formula_docs.py          # 重建业务线公式文档
└─ build_skill_business_docs.py             # 同步生成 Skill 业务线知识文档

流程执行模块/                         # 用于完成接口、数据和报告操作
.artifacts/runs/<run_id>/               # 每次运行的脱敏产物
.env                                    # 本地环境配置，不提交、不展示凭证
~~~

知识文件的边界：

- configs/knowledge/frontend-metric-matrix/*.json：页面真实可选项，回答“页面上能选什么”。
- .cursor/skills/ad-control-knowledge/authorized-scenarios.json：后端候选指标和公式信息（证据已清理，当前不可造数、不可执行）。

- configs/cases/*.json：实际执行的规则场景，包括业务线、维度、投放方式、时间范围、聚合方式、指标和比较条件。
- docs/generated/business-metrics/：脚本生成的分析和查阅材料，不是正式用例运行时的直接输入。JSON 面向机器读取，Markdown 面向人工审查；不要只修改其中的 Markdown 文件。
- 生成文档的入口是 `scripts/rebuild_business_formula_docs.py` 和 `scripts/build_skill_business_docs.py`；正式授权和造数仍以 `.cursor/skills/ad-control-knowledge/authorized-scenarios.json` 为准。

前端矩阵存在某个指标，不代表该指标已经具备后端公式、数据表字段和安全造数能力。正式执行必须经过授权知识校验。

---

## 4. 当前项目的标准执行流程

### 4.1 检查环境

在项目根目录执行，并确认使用测试数据库：

~~~powershell
$env:AD_CONTROL_DB_ENV = "test"
~~~

.env 中需要配置 API、规则执行服务、测试数据库和鉴权信息。凭证不会写入用例、报告或日志。

### 4.2 校验指标矩阵

~~~powershell
python scripts\\validate_frontend_metric_matrix.py

# 重建业务线指标、公式和汇总文档
python scripts\\rebuild_business_formula_docs.py
python scripts\\build_skill_business_docs.py
~~~

该步骤只校验知识文件，不创建规则、不写数据库。

### 4.3 预览单个用例

~~~powershell
python scripts\\run_cases.py --case configs\\cases\\cpsdy-channel-auction-today-consume-ge-10.json --dry-run
~~~

预览阶段会生成规则请求、造数计划和报告占位文件，但不会调用真实 API、规则执行服务 或数据库。

### 4.4 执行单个用例

确认用例、API、规则执行服务、测试数据库和产物目录无误后执行：

~~~powershell
python scripts\\run_cases.py --case configs\\cases\\cpsdy-channel-auction-today-consume-ge-10.json
~~~

完整执行顺序由 ad-control-api-flow 统一编排：

1. 校验用例和授权知识；
2. 创建规则并提取动态 rule_id；
3. 编译 HIT/MISS 造数；
4. 写入测试 MySQL；
5. 触发规则执行服务；
6. 轮询 ad_data_control_log；
7. 判断 HIT 或 MISS 是否符合预期；
8. 按持久化的清理清单删除测试数据；
9. 保存运行产物并生成报告。

已创建的规则默认保留，测试数据必须清理。

### 4.5 批量执行当前 CPSDY 渠道竞价当天场景

~~~powershell
python scripts\\run_cpsdy_channel_auction_today_batch.py --workers 4
~~~

该批量入口用于当前项目中的“头条端原生-付费 / 渠道维度 / 竞价投放 / 当天”场景。

也可以运行 configs/cases/ 下所有启用的用例：

~~~powershell
python scripts\\run_cases.py --all --workers 4
~~~

---

## 5. 并行和非并行运行方式

run_cases.py 的任务粒度是：

~~~text
一个 case × 一个 mode（hit 或 miss） = 一个独立任务
~~~

例如 6 个 case，每个 case 运行 hit 和 miss，一共会提交 12 个任务。

~~~powershell
# 非并行：一次只运行一个任务
python scripts\\run_cases.py --all --workers 1

# 并行：最多同时运行 4 个任务
python scripts\\run_cases.py --all --workers 4
~~~

实现方式：

- 使用 Python ThreadPoolExecutor；
- --workers 1 等价于串行执行；
- 默认 worker 数来自 AD_CONTROL_WORKERS，未配置时为 4；
- 每个线程内部仍按“创建规则 → 造数 → 规则执行服务 → 校验 → 清理”串行执行；
- 所有任务完成后，run 级 Allure 汇总报告再串行生成；
- 同一批任务共享一个 run_id，每个 case/mode 使用独立产物目录；
- 控制台结果按提交顺序输出，不代表任务实际完成顺序。

提高 worker 数会同时增加 API、规则执行服务 和测试数据库压力，不建议在没有限流和容量确认时无限增大。

---

## 6. 单独使用某个 Skill 对应的脚本

完整流程优先使用 run_cases.py。只有需要单独排查某一个阶段时，才使用以下入口。

### 6.1 规则创建

~~~powershell
# 只校验并预览请求
python scripts\\create_rule.py --case configs\\cases\\<case>.json --dry-run

# 确认后真实创建
python scripts\\create_rule.py --case configs\\cases\\<case>.json --execute
~~~

创建成功后必须使用接口返回的动态 rule_id，不能猜测或硬编码。

### 6.2 造数

~~~powershell
# 预览 HIT/MISS 造数计划
python scripts\\seed_data.py --case configs\\cases\\<case>.json --mode hit

# 确认后写入测试库
python scripts\\seed_data.py --case configs\\cases\\<case>.json --mode hit --execute --rule-id <rule_id>
~~~

### 6.3 规则执行服务 和结果校验

~~~powershell
# 预览
python scripts\\validate_result.py --rule-id <rule_id> --channel-code <channel_code> --mode hit

# 真实触发并校验
python scripts\\validate_result.py --rule-id <rule_id> --channel-code <channel_code> --mode hit --execute
~~~

HIT 必须在观察窗口内查到匹配日志；MISS 必须完整观察窗口且不能出现匹配日志。

### 6.4 清理失败恢复

每个造数任务会生成 cleanup-manifest.json。如果完整流程中断，可先预览再执行清理：

~~~powershell
python scripts\\cleanup_seed.py --manifest .artifacts\\runs\\<run_id>\\<case_id>\\<mode>\\cleanup-manifest.json
python scripts\\cleanup_seed.py --manifest .artifacts\\runs\\<run_id>\\<case_id>\\<mode>\\cleanup-manifest.json --execute
~~~

清理必须使用已落盘的清单谓词，不重新计算删除范围。

### 6.5 实测授权

~~~powershell
# 默认只预览
python scripts\\authorize_empirical.py --case configs\\cases\\<case>.json

# 真实闭环，必须显式确认
python scripts\\authorize_empirical.py --case configs\\cases\\<case>.json --execute --confirm
~~~

只有创建接口接受且 规则执行服务 日志出现 HIT 时，才会更新授权知识。

---

## 7. 报告和产物

所有运行产物统一放在：

~~~text
.artifacts/runs/<run_id>/
~~~

典型结构：

~~~text
<run_id>/
├─ <case_id>/
│  ├─ hit/
│  │  ├─ run.json
│  │  ├─ seed-plan.json
│  │  ├─ cleanup-manifest.json
│  │  ├─ validation-result.json
│  │  ├─ report/case.md
│  │  └─ report/allure/
│  └─ miss/
├─ report/summary.md
├─ report/allure/index.html
└─ batch-summary.json
~~~

报告生成不重新调用业务 API 或数据库，可以对已有运行重新生成：

~~~powershell
python scripts\\generate_reports.py --run-dir .artifacts\\runs\\<run_id>
~~~

### 7.1 正确打开 Allure

Allure 报告不是单个 HTML 文件，不能直接双击 index.html，也不要使用 file:/// 打开。

使用 HTTP 服务：

~~~powershell
python -m http.server 8877 --bind 127.0.0.1 --directory .artifacts\\runs\\<run_id>\\report\\allure
~~~

然后访问：

~~~text
http://127.0.0.1:8877/index.html
~~~

端口如果已被占用，应更换端口；必须确认打开的是当前 run_id 对应的报告目录，避免看到旧批次报告。

---

## 8. 安全和失败处理规则

1. 所有数据库写入和删除都必须满足：
   ~~~dotenv
   AD_CONTROL_DB_ENV=test
   ~~~
2. 真实执行前必须确认用例、API、规则执行服务、测试数据库和产物目录。
3. 不打印 Authorization、Cookie、token、密码、API key 或数据库密码。
4. 规则创建成功后保留规则，不自动删除规则；只清理本次造数数据。
5. 造数失败时回滚；清理失败时单独标记并保留清理清单。
6. 不臆造指标 code、数据表、字段或公式；未授权场景直接停止。
7. 不从任意外部目录生成报告；报告只能基于指定 run 目录中的产物生成。
8. 不直接打开 Allure 的 file:// 地址。

---

## 9. 常用命令速查

~~~powershell
# 单元测试
python -m pytest tests\\unit

# 校验前端指标矩阵
python scripts\\validate_frontend_metric_matrix.py

# 重建业务线指标、公式和汇总文档
python scripts\\rebuild_business_formula_docs.py
python scripts\\build_skill_business_docs.py

# 单用例预览
python scripts\\run_cases.py --case configs\\cases\\<case>.json --dry-run

# 单用例真实执行
python scripts\\run_cases.py --case configs\\cases\\<case>.json

# 全部用例并行执行
python scripts\\run_cases.py --all --workers 4

# 全部用例串行执行
python scripts\\run_cases.py --all --workers 1

# 当前 CPSDY 渠道竞价当天批量执行
python scripts\\run_cpsdy_channel_auction_today_batch.py --workers 4

# 重新生成已有报告
python scripts\\generate_reports.py --run-dir .artifacts\\runs\\<run_id>
~~~
