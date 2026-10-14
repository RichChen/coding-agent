# coding-harness 收尾计划

日期：2026-09-29。执行者：挂在 `D:\crq\src\coding-harness` 的 Cursor agent。
配套：`D:\crq\src\coding-agent\docs\sprint\AGENT-MEMORY-7-CLOSEOUT.zh-CN.md`。
依据：CHECKPOINT-6（B2 完成）、A5-MAIN-RESULTS、审计案例分析。

实验已经跑完，分析已经出了预注册结论。本轮**不调用模型、不改 runner / grader / 镜像 / 校准、不重跑任何槽位**。只做盘点、冻结收口和文档，然后停下。

## 0. 审计结论（不要改这些句子）

- 主要分析：n=56，平均 d_t −0.0179，p=0.7175，95% 区间 [−0.0833, 0.0476]。没有检出大于 13.1 个百分点的效应。
- 次要分析（预测注入 51 题）：平均 d_t 0.0000，区间 [−0.0654, 0.0654]。
- 漂移：r4 减 r1–r3 是 −0.0238；B2 减同期 r4 是 +0.0060。都是描述性的。
- 链路有效：B0 168/168、B2 168/168、r4 56/56；注入 168/168 与预测一致；没有晚于目标、目标自身或跨仓库的卡。
- 被否定的是"同仓库、更早、按规则提取的 validated_fix 卡片"这一种设计，不是实验失败。

## 1. 本轮规则

沿用全部硬约束。另外：

1. 不调用模型。花费上限 0。
2. 不改 `src/`、`scripts/run_swe_task.py`、`scripts/run_a5_main.py`、grader、镜像、校准 JSON、`runs/a5-main/` 里的运行产物。
3. 不删除、不移动 `runs/a5-main/`、`runs/a5-main-void/`、`runs/a5-main-halted/`。旧证据原样保留。
4. 不读 `runs/sprint5-main-private/`。案例数据已经写在 `docs/sprint/A5-CASE-DATA.md`。核对脚本如果需要 gold 路径，只允许在内存里取 `+++ b/` 的路径，只输出计数和路径，不打印 patch。
5. 不改 coding-agent 仓库。
6. 小步提交。不 force push。不改写历史。

日常记录仍追加到 `docs/sprint/PROGRESS.md`，标题用"第七轮 第 N 步"。完成全部步骤后写 `docs/sprint/CHECKPOINT-7.md`，停下等审计。

## 2. 分步计划

### 第 1 步：运行清单 `A5-MAIN-INVENTORY.md`

新建 `docs/sprint/A5-MAIN-INVENTORY.md`。数字从磁盘复算，不要抄 PROGRESS 里的约数。sha 用 `scripts/handoff_sha.py` 的 `handoff_sha256`。

必须包含：

1. **tag 与 commit**
   - harness：`a5-main-freeze`、`-r1`、`-r2`、`-r3`、`-r4` 各自指向的 commit。
   - coding-agent：`a5-main-freeze` 指向的 commit（读它的 `.git`，不要改那个仓库）。
2. **输入文件 sha**（冻结记录里已有的再复算一遍，对不上就停下）
   - `configs/sprint/main-targets.yaml`
   - `docs/sprint/main-accepted-ids.txt`
   - `configs/sprint/b0-v2.yaml`
   - `docs/sprint/memory-source-runs.json`
   - `docs/sprint/main-b0-runs.json`（v2）
   - `docs/sprint/b2-predicted-injection.json`
   - coding-agent 的 `benchmarks/a5/memory-cards-v6.jsonl` 的 `cards_sha256`（从它的 manifest 读，并复算 jsonl）
3. **槽位计数**（只计 `r1..r3` 和 `b0/r4`，不计 `r*.infra*`）
   - B0 r1–r3、B2 r1–r3、B0 r4 的完成数
   - infra 退役次数（分 B0 / B2 / r4）
   - 作废目录：`runs/a5-main-void/r1-tool-py36/` 和 `r2-no-issue/` 各有多少个运行目录、花费合计
   - 两次按规则重评的运行：django-13964 B2 r3（`grader_candidate_error=execution`）、sphinx-7590 B2 r3（`execution_timeout`）
4. **花费**
   - `runs/a5-main/` 总额（有效实验）
   - B0 r1–r3、B2、r4 各自合计与平均
   - 两批作废花费
   - canary 花费（修订期间、已计入或未计入 `runs/a5-main/` 的，分开写）
   - 以上相加，给出冲刺第 6 轮合计；再从 PROGRESS 把第 1–5 轮花费抄过来，给出项目模型花费合计，并注明第 6 轮之前的数字来自 PROGRESS，本文件只对第 6 轮做复算
5. **检查结果摘要**（从 CHECKPOINT-6 抄，并与 `runs/a5-main-logs/b2-stats.json` 核对）
   - 隔离失败 0
   - `harness_tool_errors` 0
   - 注入一致 168/168
   - 全量检查三项 0

提交这一步。

### 第 2 步：核对案例数据

`docs/sprint/A5-CASE-DATA.md` 已由审计写好。用 `.tmp/case_mem.py table` 和 `follow` 复跑（需要把 agent 仓库加进 `sys.path`，用本仓库 `.venv`）。

- 输出必须与 `A5-CASE-DATA.md` 的第 1、2 节一致：51/9/42、平均 d、9 道重合表、153 次里 5 次打开、0 次最终改在卡片独有文件。
- 不一致就停下，不要改数据文件，写进 CHECKPOINT 等审计。
- 一致则在 `A5-CASE-DATA.md` 文首加一行：`核对：<commit>，table/follow 与正文一致。`

不要新做分析，不要加新案例。

### 第 3 步：冻结收口

在 `docs/sprint/A5-MAIN-FREEZE.md` 末尾追加一节 **「收口」**，不要改前面的修订正文。写明：

- 实验运行已结束，不再接受对 runner / grader / 镜像 / 校准的改动。
- 主要分析和次要分析以 coding-agent 的 `docs/sprint/A5-MAIN-RESULTS.zh-CN.md` 为准；最终叙述以 `coding-agent/docs/A5-FINAL-REPORT.zh-CN.md` 为准（agent 侧收尾后才会有）。
- 案例数据以本仓库 `docs/sprint/A5-CASE-DATA.md` 为准。
- 清单以 `docs/sprint/A5-MAIN-INVENTORY.md` 为准。
- 不打新的 freeze tag。若审计要求，再打 `a5-main-closeout`。

### 第 4 步：文档入口

1. 在 `README.zh-CN.md` 和 `README.md` 靠近文首处加一段「A5-main」：一句话结果（没有检出大于 13.1 个百分点的效应；B0 68.5%），链接到 `docs/PROJECT-HISTORY.zh-CN.md`、`docs/sprint/A5-MAIN-DESIGN.zh-CN.md`、`docs/sprint/A5-MAIN-INVENTORY.md`，以及 agent 仓库的结果报告和最终报告路径。不要改旧的 H3/H4/H5/R1/R2 叙述。
2. `docs/sprint/PROGRESS.md` 追加第七轮各步。
3. 写 `docs/sprint/CHECKPOINT-7.md`：各步提交、清单 sha、案例核对结果、测试结果。**通知 coding-agent：清单和案例数据已就绪，可以写最终报告。**

### 第 5 步：测试与停下

`.\.venv\Scripts\python.exe -m pytest -q`。通过数记进 CHECKPOINT-7。全量测试通过、工作区只剩本轮文档改动后停下。

## 3. 不要做的事

- 不要根据案例去改卡片、检索或 prompt。
- 不要重跑 B0 / B2，不要开同题重试实验。
- 不要把作废运行混进清单的"有效运行"计数。
- 不要在文档里贴 gold patch、test patch 或 F2P/P2P 原文。
