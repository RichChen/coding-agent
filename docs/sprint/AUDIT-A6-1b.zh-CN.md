# 审计：A6-1b（两侧）

日期：2026-10-13。审计对象：harness `92bad7a` 的 `CHECKPOINT-A6-1b.md`，coding-agent `e9901b5` 的 `CHECKPOINT-A6-1b.md`。

**结论：两侧通过。agent 侧还要改一处小地方（第 2 节）；改完之后 harness 进入 A6-2（冻结和 canary）。**

审计核对过：两份 CHECKPOINT；两边的提交记录；agent 的 tag `a6-retry-freeze-r1` → `01db102`，和 agent CHECKPOINT 一致；harness 工作区是干净的；agent 工作区除了本轮之前就有的 `docs/memory-v2/`，也是干净的。审计没有重跑测试、preflight 或 mock，这些数字以 CHECKPOINT 为准。

## 1. harness 侧四个待决项

1. **不接 `fault_alarm`：认可。** A6 的题全是 A5 失败过的，"连续全不解出"不能说明 harness 出了故障。harness 故障由 infra 比例、隔离检查、grader missing 和 `harness_tool_errors` 来覆盖。
2. **`harness_tool_errors > 0` 就停：保留。** 这是 A5 的规则，A5 全程是 0。在冻结记录里写明它是第 1 节之外沿用的条件。
3. `slots_expected` 和 mock 的 `note` 字段：认可。
4. 重写 `receipt.json`：认可，内容和 A5 相同。

另外两点：

- canary 的 4 个槽位正好是队列前 4 个（2 个 R0、2 个 R1），符合计划。canary 是正式运行的一部分，A6-3 续跑时不要重跑这 4 个。
- 第一次 preflight 时 Docker Desktop 中途停了。A6-2 跑 canary 之前，在同一次开机里重跑一次 `--preflight`。正式运行期间 Docker 如果再停，会表现为 infra_error，由 10% 的停止线兜底，不要手动重启后接着跑而不记录。

## 2. agent 侧：`attempts_sha256` 不一致必须 STOP

现在的做法是：`a6-retry-runs.json` 的 `attempts_sha256` 和清单的 `handoff_sha256` 不一致时，只在报告开头标一句"不一致"。这样分析的记录和运行时注入的记录可能不是同一份。改为 STOP，理由写 `attempts_sha_mismatch`，并加测试。同理，runs 文件和清单两个交接文件的 sha，如果和启动参数里给出的期望值不同，也要 STOP。

改完重跑合成数据，确认结论不变。`a6-retry-freeze-r1` 不动，打 `a6-retry-freeze-r2`。

X 的新写法认可：零效应时 X=7.7pp、区间上限 6.8pp，两者口径不同，报告里同时给出就行。85 个 error 四次都没有复现，记为未解释的偶发问题，不阻断。

## 3. A6-2 的要求（在计划第 5 节 A6-2 之外补充）

- 开工第 0 步：确认 agent 仓库已有 tag `a6-retry-freeze-r2`，并且 agent 的 `CHECKPOINT-A6-1c.md` 写明了它指向的 commit。两者缺一就立即停下，不冻结，不跑 canary。
- 冻结记录 `A6-R-FREEZE.md` 除了计划列出的项目，还要写：agent tag `a6-retry-freeze-r2` 和它的 commit；模板 sha `7bed7ba8…`；清单 sha `bd932529…`；canary 的 4 个槽位；沿用的停止条件（`harness_tool_errors`）；`PARALLEL=3`；打乱种子 `20261013`。
- harness 打 tag `a6-retry-freeze`。
- canary 前重跑 `--preflight`，22/22 通过才继续。
- canary 4 次都完成后，CHECKPOINT-A6-2 要写：每次的 status、solved、model_calls、cost_cny、stop_reason；模型名和 base_url 主机；R1 一份完整的第一条 user 消息（用 django-15022 r1 那个槽位）；累计花费；注入核对 4/4。canary 的 solved 只记录，不解读。
- 任何停止条件被触发，或者单次花费超过 1.5 元，都停下写 CHECKPOINT，不进入 A6-3。
