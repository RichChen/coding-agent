# CHECKPOINT-7：A5-main 收尾（coding-harness）

日期：2026-09-29。依据：`docs/sprint/HARNESS-SPRINT-7-CLOSEOUT.zh-CN.md`。

**结论：收尾计划的第 1–5 步都已完成。清单数字从磁盘复算，与冻结记录和 CHECKPOINT-6 一致；案例数据核对一致；冻结记录已收口。** 本轮没有调用模型（花费 0），没有改 `src/`、runner、grader、镜像、校准 JSON，也没有移动或改写 `runs/a5-main/`、`runs/a5-main-void/`、`runs/a5-main-halted/`。没有读 `runs/sprint5-main-private/`（案例核对脚本只在内存里取 gold 的 `+++ b/` 路径）。没有改 coding-agent 仓库，没有打新 tag，没有 push。

全量测试有 1 个失败，是本轮之前就存在的，与收尾改动无关，详见"测试"一节，需要审计决定是否处理。

## 各步提交

| 步 | 内容 | 提交 |
| --- | --- | --- |
| 第 1 步 | 只读脚本 `scripts/sprint7_inventory.py` 和 `docs/sprint/A5-MAIN-INVENTORY.md` | `f06d00f` |
| 第 1 步 | 修正 PROGRESS 第 1 步记录里被 shell 吞掉的反引号（只改文字） | `c85886c` |
| 第 2 步 | `A5-CASE-DATA.md` 文首加核对行 | `47f459b` |
| 第 3 步 | `A5-MAIN-FREEZE.md` 末尾追加「收口」 | `4d55a6f` |
| 第 4 步 | 审计提供的 `docs/PROJECT-HISTORY.zh-CN.md` 和本轮收尾计划原样入库（此前未跟踪，README 要链接前者） | `dd17bb3` |
| 第 4 步 | 两个 README 加「A5-main」入口；PROGRESS 空行修正 | `aec35c8` |
| 第 4、5 步 | 本文件和 PROGRESS 第 4、5 步 | 本次提交 |

## 清单（第 1 步）

`docs/sprint/A5-MAIN-INVENTORY.md` 的 sha（`handoff_sha256`）：`e277cfefaeb30948f202888de999f0f6335ea581b56bd256fceaefea0d5be9ec`。脚本输出 `runs/a5-main-logs/inventory.json` 的 sha：`61b4bacfe0a5525549639c77207ac8fc9d96049cac1cb96c4f93c50f125fabd6`。

- **tag：** harness 的 `a5-main-freeze` → `02c8671`、`-r1` → `fb26dbd`、`-r2` → `2f28232`、`-r3` → `1707d23`、`-r4` → `074219c`；coding-agent 的 `a5-main-freeze` → `a22e4ca`。
- **输入 sha：** `main-targets.yaml`、`main-accepted-ids.txt`、`b0-v2.yaml`、`memory-source-runs.json`、`main-b0-runs.json`（v2）、`b2-predicted-injection.json` 六个文件都与冻结记录一致；v6 卡片的 manifest `cards_sha256`、jsonl 复算值和冻结值三者相同（`3416eb9d…`，70 张，`status: final`）。
- **槽位：** B0 r1–r3 168/168，B2 r1–r3 168/168，B0 r4 56/56。infra 退役 B0 2 次、B2 3 次、r4 2 次，都只重跑一次。
- **按规则重评：** django-13964 B2 r3（`execution`）、sphinx-7590 B2 r3（`execution_timeout`），都是 `solved=false`，没有重跑。
- **作废：** `r1-tool-py36` 25 个运行目录、13.682 元；`r2-no-issue` 38 个（含 2 个 infra 目录）、24.055 元。两处都与各自的 `void-runs.json` 一致。
- **花费：** `runs/a5-main/` 有效实验 131.804 元（B0 r1–r3 55.774，B2 57.790，r4 18.240），与 `b2-stats.json` 相同。第 6 轮合计 169.541 元（有效 131.804 + 作废 37.737 + 停止目录 0）。canary 按修订分开列出：修订 0–2 的 3.739 元已经包含在作废花费里，修订 3 的 1.733 元已经包含在 B0 r1–r3 里，都不重复相加。第 1–5 轮从 PROGRESS 抄录，共 43.422 元，项目模型花费合计 212.963 元。
- **检查：** 399 份 summary 中隔离失败 0，`harness_tool_errors` 0，未分类的 missing 和 grader reason 都是 0；注入 168/168 一致；全量检查三项都是 0。

## 案例核对（第 2 步）

用本仓库 `.venv` 复跑 `.tmp/case_mem.py table` 和 `follow`。结果与 `docs/sprint/A5-CASE-DATA.md` 第 1、2 节一致：

- 注入卡片的题 51 道，卡片文件与 gold 文件有重合的 9 道，没有重合的 42 道；
- 平均 d_t：有重合 −0.074，没有重合 +0.016，未注入 5 道 −0.200；
- 9 道重合题的 B0/B2、共享文件和注入卡片逐行相同；
- 153 次注入运行里，5 次打开过卡片独有的文件，0 次最终改在这类文件上，5 次的题和槽位与正文表格相同。

第 3 节 17 道 d_t ≠ 0 的题也一致。文首已加 `核对：c85886c，table/follow 与正文一致。`，数据没有改动。没有做新分析，也没有加新案例。

**请审计看一处文字：** `A5-CASE-DATA.md` 开头写"coding-agent 写最终报告时引用本文件第 7 节"，但文件只有第 1–4 节。我没有改，由审计决定应该引用哪一节。

## 冻结收口（第 3 步）

`A5-MAIN-FREEZE.md` 末尾追加了「收口」一节，前面的修订正文没有改动。内容包括：实验运行结束，不再接受对 runner、grader、镜像或校准的改动；分析以 coding-agent 的 `A5-MAIN-RESULTS.zh-CN.md` 为准；最终叙述以 `A5-FINAL-REPORT.zh-CN.md` 为准；案例数据以 `A5-CASE-DATA.md` 为准；清单以 `A5-MAIN-INVENTORY.md` 为准；不打新 freeze tag，审计要求时再打 `a5-main-closeout`。

## 文档入口（第 4 步）

`README.zh-CN.md` 和 `README.md` 在简介句后面加了「A5-main」一段：B0 解出率 68.5%，没有检出大于 13.1 个百分点的效应。段落链接到项目历程、A5-main 设计、运行清单，以及 agent 仓库的结果报告和最终报告。最终报告目前还不存在，链接旁边注明由 agent 侧收尾后生成。旧的 H3/H4/H5/R1/R2 段落没有改动。

## 测试（第 5 步）

`.\.venv\Scripts\python.exe -m pytest -q`：**620 passed，1 failed，22 skipped。**

- 失败的测试是 `tests/test_summary_wrapper.py::test_one_call_no_summary_private_grading_and_durable_replay`。它断言模型收到的消息与 `make_view` 完全相同，但 `src/runtime/loop.py` 会在消息末尾追加一条 `remaining model calls: 1/1`。这条提示是 2026-09-24 的 `dd77ba3` 加进来的，晚于这个测试最后一次修改（`a53d29d`）。
- 这个失败早就存在：在本轮之前的 `03fe586` 和 tag `a5-main-freeze-r4` 上用同一个 `.venv` 都能复现。它与本轮改动无关，也不涉及 A5-main 用到的路径。
- 之前各轮记录的"444 passed，199 skipped"是用系统 Python 跑的，那个环境缺少依赖，这个测试文件整个被跳过。本轮用系统 Python 再跑一次，仍是 444 passed，199 skipped。
- 用 `.venv` 排除这个测试后：620 passed，22 skipped。
- 修复要么改 `src/`，要么改测试期望，超出了本轮只改文档的范围，所以我没有动。需要审计决定。

工作区里除本轮提交外，没有 `docs/`、`scripts/`、`src/`、`tests/`、`configs/` 或 README 的未提交改动。

## 通知 coding-agent

清单（`docs/sprint/A5-MAIN-INVENTORY.md`）和案例数据（`docs/sprint/A5-CASE-DATA.md`，已核对）已经就绪，可以写最终报告。花费、槽位和 tag 请引用清单；案例请引用 `A5-CASE-DATA.md`（"第 7 节"的引用见上文，等审计确认）。

停在这里，等审计。
