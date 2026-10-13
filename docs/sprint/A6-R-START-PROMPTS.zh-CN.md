# A6-R 启动 prompt

两个 Cursor agent 同时开工，各自做完 A6-1 停下。之后每一轮由审计侧发新的一句话 prompt（见文末）。

## 发给 coding-harness agent

请执行 `D:\crq\src\coding-harness\docs\sprint\A6-R-PLAN.zh-CN.md` 里 harness 侧的 A6-1（第 5 节），并遵守第 1、3、4、7 节。

开工前完整读取本计划、`docs/sprint/HANDOFF-CONVENTIONS.md`、`docs/sprint/CHECKPOINT-7.md`、`docs/sprint/A5-MAIN-INVENTORY.md`，以及 `scripts/run_a5_main.py` 和 `scripts/run_swe_task.py::run_task`。背景可读 `D:\crq\src\coding-agent\docs\memory-v2\OPTIONS.zh-CN.md` 方案 A。

本轮不调用任何真实模型，不启动 provider。A5 的运行目录只读，不改 `run_a5_main.py`。第一次尝试的复算数如果不是 53 次、22 道题，立即停下写 CHECKPOINT。泄漏检查脚本读私有材料时只输出计数和命中位置，不要把 gold、test patch、F2P/P2P 内容打印到终端、日志或提交里。泄漏检查 1–3 项有任何命中都停下等审计，不要自己改模板绕过。

做完写 `docs/sprint/CHECKPOINT-A6-1.md` 和 PROGRESS，小步提交，不 push，然后停下。

## 发给 coding-agent agent

请执行 `D:\crq\src\coding-harness\docs\sprint\A6-R-PLAN.zh-CN.md` 里 coding-agent 侧的 A6-1（第 6 节），并遵守第 1、7 节。

开工前读取本计划、`docs/sprint/A5-MAIN-RESULTS.zh-CN.md`、`scripts/analyze_a5_main.py`（统计方法和种子写法照它来）。预注册文件把计划第 1 节原样写入，不要增删指标。分析脚本必须在任何真实 A6 数据出现之前提交，并用三套合成数据跑通。diff 归一化规则必须和 harness 的 `scripts/build_a6_attempts.py` 一致；harness 侧还没写完时，先按计划第 3 节实现，并加一个测试，等 harness 提交后再比对。

不调用模型，不改 coding-harness 仓库。做完打 tag `a6-retry-freeze`，写 `docs/sprint/CHECKPOINT-A6-1.md`，小步提交，不 push，然后停下。

## 后续轮次（审计通过后发）

- harness A6-2：`A6-1 审计通过。请执行 A6-R-PLAN 第 5 节 A6-2：写冻结记录、打 tag、跑 4 次 canary，写 CHECKPOINT-A6-2 后停下。agent 侧 tag 指向 <commit>。`
- harness A6-3：`A6-2 审计通过。请执行 A6-R-PLAN 第 5 节 A6-3，停止条件按第 1 节，写 a6-retry-runs.json 和 CHECKPOINT-A6-3 后停下。不要计算 R1−R0。`
- agent A6-4：`harness 的 a6-retry-runs.json 已提交，handoff_sha256 = <sha>。请执行 A6-R-PLAN 第 6 节 A6-4，写 A6-R-RESULTS 和 CHECKPOINT-A6-4 后停下。`
