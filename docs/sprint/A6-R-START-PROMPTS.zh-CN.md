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

## A6-1b（A6-1 审计后发）

### 发给 coding-harness agent

A6-1 审计结果在 `D:\crq\src\coding-harness\docs\sprint\AUDIT-A6-1.zh-CN.md`，开工前完整读取。泄漏检查第 1、2 项的命中不阻断，判定口径改为"记录内容只能来自第一次运行的产物和原始源码"。

请按审计第 4 节做：
1. 补一个测试：私有材料不可读或换成垃圾内容时，渲染出的 53 份记录逐字节不变；
2. 按审计第 2 节改 "Files changed" 的 none 文字，重建记录，提交 `docs/sprint/a6-attempts/` 和 `a6-attempts.json`；
3. 继续计划第 5 节 A6-1 的第 3–6 步（runner、`--preflight`、mock 端到端、全量测试）。`a6-retry-runs.json` 的字段以 coding-agent 的 `docs/sprint/A6-R-PREREG.zh-CN.md`"输入文件约定"一节为准。mock 端到端的最后一步用 agent 仓库 tag `a6-retry-freeze-r1` 上的 `scripts/analyze_a6_retry.py` 读 mock 的 runs 文件，确认它因为 mock 而 STOP。这一步只读 agent 仓库，不改它；如果那个 tag 还不存在，就跳过这一步并在 CHECKPOINT 里注明。

本轮不调用真实模型。做完写 `docs/sprint/CHECKPOINT-A6-1b.md` 和 PROGRESS，小步提交，不 push，不打 freeze tag，然后停下。

### 发给 coding-agent agent

A6-1 审计结果在 `D:\crq\src\coding-harness\docs\sprint\AUDIT-A6-1.zh-CN.md`，开工前读第 1、3 节。请做：
1. 结论句里的 X 改为 2.8 × s_obs / √N（s_obs 是实际 d_t 的样本标准差），同时报 95% 区间上限。预注册第 1 节不动，只改"脚本实现口径"一节；
2. `a6-attempts.json` 以 harness 的实际结构为准：列表在 `records`，计数在 `attempts`。预注册"输入文件约定"一节改成这样，脚本只接受 `records`；
3. harness 会按审计第 2 节改 "Files changed" 的文字，并重建记录。diff 段不受影响，但等 harness 提交新记录后，要重跑 `tests/test_a6_diff.py` 的逐字节比对；
4. 重跑合成数据，确认三套结论不变，更新 `A6-R-SYNTHETIC-REPORT.md`；再跑两次全量测试，记下结果，看那 85 个 error 会不会复现；
5. 保留 `a6-retry-freeze` 不动，打 `a6-retry-freeze-r1`。

不调用模型，不改 coding-harness。写 `docs/sprint/CHECKPOINT-A6-1b.md`，小步提交，不 push，然后停下。

## 后续轮次（审计通过后发）

- harness A6-2：`A6-1 审计通过。请执行 A6-R-PLAN 第 5 节 A6-2：写冻结记录、打 tag、跑 4 次 canary，写 CHECKPOINT-A6-2 后停下。agent 侧 tag 指向 <commit>。`
- harness A6-3：`A6-2 审计通过。请执行 A6-R-PLAN 第 5 节 A6-3，停止条件按第 1 节，写 a6-retry-runs.json 和 CHECKPOINT-A6-3 后停下。不要计算 R1−R0。`
- agent A6-4：`harness 的 a6-retry-runs.json 已提交，handoff_sha256 = <sha>。请执行 A6-R-PLAN 第 6 节 A6-4，写 A6-R-RESULTS 和 CHECKPOINT-A6-4 后停下。`
