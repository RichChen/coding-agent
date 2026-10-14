# A5-main 运行清单

日期：2026-09-29。数字由 `scripts/sprint7_inventory.py` 从磁盘复算，输出在 `runs/a5-main-logs/inventory.json`。sha 用 `scripts/handoff_sha.py` 的 `handoff_sha256`（换行统一为 LF）；卡片文件按原始字节计算 `cards_sha256`，与 D5 的核对口径相同。

只统计 `runs/a5-main/` 里的有效运行。作废目录和停止目录单独列出，不计入有效运行。

## 1. tag 与 commit

| 仓库 | tag | commit |
| --- | --- | --- |
| coding-harness | `a5-main-freeze` | `02c8671d3afb4be51533f00fe12b8074ecefbb56` |
| coding-harness | `a5-main-freeze-r1` | `fb26dbd8def7055cb2602dca4a737392f6e4b8c5` |
| coding-harness | `a5-main-freeze-r2` | `2f28232a0d35cad254cc1222cb2d35a94d84cfcc` |
| coding-harness | `a5-main-freeze-r3` | `1707d230729d4faa450ea89d357eb01e197280e8` |
| coding-harness | `a5-main-freeze-r4` | `074219cf971e3e3389eff38f80804a345cdd3785` |
| coding-agent | `a5-main-freeze` | `a22e4ca0a3994012c167a3e02e06498731c24a18` |

coding-agent 的 tag 是只读查询得到的，没有改动那个仓库。

## 2. 输入文件 sha

全部与冻结记录（`A5-MAIN-FREEZE.md`）一致。

| 文件 | sha256 |
| --- | --- |
| `configs/sprint/main-targets.yaml` | `3556a5fdfac8b7d4ac2b631a31e2a7951312523aff605014f3b32eaf184738a4` |
| `docs/sprint/main-accepted-ids.txt` | `d71cb17adb44fd06f71bf8b0f8babcac12ea839354f1dcec30aae2ffa719b730` |
| `configs/sprint/b0-v2.yaml` | `ddf53b2db293bf03c7a099a43a34ea96aee5ecca365d9b8b4f11d66afb344e60` |
| `docs/sprint/memory-source-runs.json`（dev 交接） | `984826707e8f69ad9b900134bd244c6056f2d8860f3036a3606bfc60b4bcb450` |
| `docs/sprint/main-b0-runs.json`（v2） | `fe0f47b8df67730a0335d7109631dc09bc4d6b5d19a601acfec0963f5dcb1f8c` |
| `docs/sprint/b2-predicted-injection.json` | `5d858eb4f3ab368fc655b310168e2c77de311ddfee4f77c0928e4d08ba79e3e5` |
| coding-agent `benchmarks/a5/memory-cards-v6.jsonl`（`cards_sha256`） | `3416eb9d8f6119081330fb3b0a2d612b8fde4678d6ec1c73a7fc681cedfcfc70` |

卡片：manifest 里的 `cards_sha256` 与 jsonl 复算值相同，manifest `status: final`，共 70 张卡。

## 3. 槽位计数

只计 `r1..r3` 和 `b0/r4`，不计 `r*.infra*`。

| 组 | 应跑 | 完成 | infra 退役 |
| --- | --- | --- | --- |
| B0 r1–r3 | 168 | 168 | 2：sklearn-14710 r1、sympy-14248 r2 |
| B2 r1–r3 | 168 | 168 | 3：django-13964 r3、pytest-5631 r1、sphinx-9461 r2 |
| B0 r4（漂移对照臂） | 56 | 56 | 2：sklearn-12585 r4、sphinx-7910 r4 |

每个 infra 槽位都退役为 `r<k>.infra1` 并重跑一次完成，没有槽位用到第二次重跑。

**按规则重评的两次运行**（都没有重跑，原 summary 保留为同目录的 `summary.pre-regrade.json`，`solved=false`）：

| 运行 | `grader_candidate_error` | 依据 |
| --- | --- | --- |
| django-13964 B2 r3 | `execution` | 冻结修订 4 补记 2（missing_regrade） |
| sphinx-7590 B2 r3 | `execution_timeout` | 冻结修订 4 补记 3 |

**作废目录**（不计入有效运行）：

| 目录 | 运行目录 | 其中 infra 目录 | 花费（元） | 作废原因 |
| --- | --- | --- | --- | --- |
| `runs/a5-main-void/r1-tool-py36/` | 25 | 0 | 13.682 | 修订 2 之前的全部 B0：Python 3.9 以下镜像里结构化工具报错 |
| `runs/a5-main-void/r2-no-issue/` | 38 | 2 | 24.055 | 修订 3 之前的全部 B0：prompt 里没有 issue 文本 |

两处的磁盘统计与各自的 `void-runs.json` 一致（运行数和花费都相同）。

另有 `runs/a5-main-halted/` 1 个运行目录（修订 0 的 sphinx-8593 canary，隔离检查失败，没有模型调用，花费 0）。

## 4. 花费

单位：元（CNY）。平均值给出两种口径：按完成槽位平均，和按全部运行目录（含 infra 目录）平均；CHECKPOINT-6 用的是后一种。

| 组 | 完成槽位花费 | infra 目录花费 | 合计 | 平均（每完成槽位） | 平均（每运行目录） |
| --- | --- | --- | --- | --- | --- |
| B0 r1–r3 | 55.343 | 0.431 | 55.774 | 0.332 | 0.328 |
| B2 r1–r3 | 57.036 | 0.754 | 57.790 | 0.344 | 0.338 |
| B0 r4 | 18.031 | 0.209 | 18.240 | 0.326 | 0.314 |
| **`runs/a5-main/` 合计（有效实验）** | | | **131.804** | | |

`runs/a5-main-logs/b2-stats.json` 的 `spent_total_cny` 也是 131.804。

**作废花费：** `r1-tool-py36` 13.682，`r2-no-issue` 24.055，合计 37.737。`a5-main-halted` 为 0。

**canary 花费**（按修订分开）：

| 修订 | commit | 运行 | 所在目录 | 花费 | 是否计入 `runs/a5-main/` |
| --- | --- | --- | --- | --- | --- |
| 修订 0 | `02c8671` | django-13964 r1、sklearn-13142 r1 | `a5-main-void/r1-tool-py36` | 0.574 + 0.113 = 0.687 | 否，计入作废花费 |
| 修订 0 | `02c8671` | sphinx-8593 r1 | `a5-main-halted` | 0.000 | 否 |
| 修订 1 | `fb26dbd` | sphinx-8593 r1 | `a5-main-void/r1-tool-py36` | 0.467 | 否，计入作废花费 |
| 修订 2 | `2f28232` | sklearn-14053、django-13964、pytest-7490、django-16527 各 r1 | `a5-main-void/r2-no-issue` | 0.875 + 0.494 + 0.627 + 0.589 = 2.585 | 否，计入作废花费 |
| 修订 3 | `1707d23` | django-13964、pytest-7205、sklearn-13142、sphinx-8593、sympy-16766 各 r1 | `a5-main` | 0.483 + 0.529 + 0.066 + 0.457 + 0.198 = 1.733 | 是，作为 B0 r1 槽位计入 |

未计入 `runs/a5-main/` 的 canary 合计 3.739 元，已经包含在作废花费 37.737 元里；计入的 1.733 元已经包含在 B0 r1–r3 的 55.774 元里。canary 不另外相加。

**冲刺第 6 轮合计：** 有效实验 131.804 + 作废 37.737 + 停止目录 0 = **169.541 元**。

**项目模型花费合计：**

| 轮次 | 花费（元） | 来源 |
| --- | --- | --- |
| 第 1 轮 | 1.798 | PROGRESS "第 2 步：B0 能力改造" |
| 第 2 轮 | 4.390 | PROGRESS "第二轮 第 5 步" |
| 第 3 轮 | 16.173 | PROGRESS "第三轮 第 5 步"、"第 10 步" |
| 第 4 轮 | 14.712 | PROGRESS "第四轮 R4-4" |
| 第 5 轮 | 6.349 | PROGRESS "第五轮 第 6 步"（重跑 0.478 + B2 冒烟 5.871） |
| 第 6 轮 | 169.541 | 本文件复算 |
| **合计** | **212.963** | |

第 1–5 轮的数字是从 PROGRESS 抄来的，本文件只对第 6 轮做了复算。

## 5. 检查结果摘要

来自 CHECKPOINT-6，并与 `runs/a5-main-logs/b2-stats.json` 和 `runs/a5-main/` 下的 399 份 summary（392 个完成槽位加 7 个 infra 目录）核对：

| 项 | 结果 |
| --- | --- |
| 隔离失败 | 0 |
| `harness_tool_errors` | 0 |
| 未分类的 grader missing / grader reason | 0 / 0（仅有的两次都已按规则分类，见第 3 节） |
| 注入一致 | 168/168 |
| 全量检查：晚于目标题的卡 / 目标题自己的卡 / 跨仓库的卡 | 0 / 0 / 0 |
