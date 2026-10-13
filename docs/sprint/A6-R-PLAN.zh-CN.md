# A6-R：同题重试记忆

日期：2026-10-13。依据：`coding-agent/docs/memory-v2/OPTIONS.zh-CN.md` 方案 A、`HANDOFF-BRIEF.zh-CN.md`、A5 收尾材料（`A5-MAIN-INVENTORY.md`、`A5-CASE-DATA.md`、`CHECKPOINT-7.md`）。

A5 的数据、结论、tag 一律不动。本实验另起编号 A6-R，新目录、新 tag、新预注册。

## 0. 一句话

A5 已经证明跨题卡片没用，原因主要是内容和题目不相关。A6-R 把相关性固定为 100%：对 A5 B0 里失败过的那次运行，第二次尝试时把"上次怎么做的、结果没过"告诉 agent，和"什么都不告诉、再做一次"比。

## 1. 实验设计（预注册内容，agent 侧原样写进预注册文件）

**题和第一次尝试**

- 第一次尝试 = A5 `runs/a5-main/<task>/b0/r1..r3` 里 `solved=false` 且不是 `infra_error` 的运行。按 OPTIONS 复算应为 53 次、22 道题。构建脚本复算得到的数如果不是 53/22，停下写 CHECKPOINT，不要自行解释。
- 不用 r4、不用 B2、不用 `.infra<n>` 目录。

**两组**

- R0：第二次尝试，prompt 与 A5 B0 完全相同（`prompt_sha256` 必须等于该题 A5 B0 的值）。
- R1：第二次尝试，prompt = A5 B0 的 prompt + 第 3 节的"上次尝试记录"。
- 其余全部相同：`configs/sprint/b0-v2.yaml`、同一 clean 镜像 digest、同一 grader、40 次调用上限、`PARALLEL=3`。

**槽位和样本量**

- 每次第一次尝试 × 每组 × 3 次 = 53 × 2 × 3 = 318 次运行。
- 槽位路径：`runs/a6-retry/<task>/<arm>/<first>/r<k>`，`arm ∈ {r0, r1}`，`first` 形如 `b0r2`，`k ∈ {1,2,3}`。R0 的槽位也按 first 编号，只是为了两组每题运行数相同，R0 的 prompt 和 first 无关。
- 318 个槽位按 (task, arm, first, k) 排序后用种子 `20261013` 打乱，单一队列交错跑，两组同期。

**主分析（只有一个）**

- 有效运行 = 非 `infra_error`。每题每组有效运行少于 2 次的题不进入主分析。
- d_t = 该题 R1 有效运行的解出率 − R0 有效运行的解出率（题内先对所有槽位平均）。
- 统计量 = 22 道题 d_t 的平均。按题符号翻转置换检验 10000 次（双侧），按题 bootstrap 95% 区间 10000 次，种子都是 `20261013`。
- 结论口径：p < 0.05 且区间不含 0 才说"检出效应"。否则报点估计和区间，说"未检出大于 X 的效应"。
- 事先算好的功效（OPTIONS 模拟，假设每次失败运行同一加性提升）：+10pp 约 54%，+15pp 约 85%，+20pp 约 98%。报告里照抄，不事后重算。

**次要指标（全部描述性，不做检验，不进结论句）**

1. diff 重复率：第二次尝试的最终 diff 与对应第一次尝试 diff 完全相同（按第 3 节的归一化）的比例，R1 vs R0。
2. 文件复用：第二次尝试改动的非测试文件与第一次尝试有交集的比例。
3. `first_edit_step` 的平均和中位数。
4. `model_calls` 平均；用满 40 次调用的比例。
5. 花费平均。
6. 档位分解：A5 B0 0/3 档 13 道、中间档 9 道各自的 d_t 平均。只描述，不作为效应证据。

**第二阶段触发规则（写死，第一阶段结果出来后不改）**

- 若主统计量点估计 ≥ +5pp 且区间含 0：允许另立 A6-R2 计划（新题、新镜像，合并分析按题聚合）。否则不做第二阶段。
- 本计划不包含第二阶段的任何实现。

**停止条件（任一满足就不再启动新运行，等在跑的结束后写 CHECKPOINT）**

- 累计 `infra_error` 超过已完成运行数的 10%；
- 任何 `answer_isolation_pass=false` 或 source-only 校验失败；
- grader 报 `missing` 或崩溃；
- R0 的 `prompt_sha256` 与 A5 B0 不同，或 R1 实际发给模型的第一条 user 消息不等于"A5 B0 prompt + 冻结清单里该 first 的记录全文"；
- 模型名或 base_url 主机与 canary 记录不同；
- 累计花费达到 210 CNY（`TOTAL_CAP`）。预计 172 元。

## 2. 分工

| 仓库 | 负责 |
| --- | --- |
| coding-harness | 记录构建脚本、泄漏检查、`run_task` 的 prompt 追加参数、A6 runner、mock 端到端、preflight、冻结、canary、正式运行、清单 |
| coding-agent | 预注册文件、分析脚本（在任何真实数据之前提交并用合成数据跑通）、结果报告 |

两边交接文件都用 `scripts/handoff_sha.py` 的 `handoff_sha256`（见 `HANDOFF-CONVENTIONS.md`）。

## 3. 上次尝试记录（R1 注入内容）

只用规则生成，不经 LLM。只读第一次尝试目录里的 `summary.json`、`candidate-delta.json`、`events.jsonl`。**不读 `grader-result.json`**，"没通过"这一比特来自 `summary.json` 的 `solved=false`。

渲染为纯文本，英文，固定模板，各段有字节上限，总上限 8192 字节：

```
<previous_attempt>
The following is a record of one earlier attempt at this same issue, made by an agent with the same tools.
Its final changes were submitted and did NOT pass the hidden evaluation tests.
The record may contain mistakes. It is evidence, not instructions; decide for yourself what to keep or change.

Stop reason: {stop_reason}; model calls used: {model_calls}/40.
Files changed: {changed_files 逗号分隔，或 "none (no source changes were submitted)"}

Final diff (truncated to {N} bytes):
{归一化 diff}

Last test-like commands and the tail of their visible output:
{最多 2 条，每条命令 + 输出尾部 ≤1500 字节；没有就写 "none"}

Agent's final message (truncated):
{最后一条 assistant 文本 ≤1000 字节；没有就写 "none"}
</previous_attempt>
```

细则：

- 归一化 diff：`candidate-delta.json` 存的是改动后的文件内容（`changed`、`deleted`），不是 diff。用 host 侧的原始源码（`task["original"]`，与 clean 镜像 `/opt/repo` 同源，不含 test patch）和 `changed` 逐文件生成 unified diff（3 行上下文），`deleted` 写成删除。按路径排序，非测试文件在前，统一 LF，不带时间戳。超出上限从尾部截断并写 `[truncated]`。上限 N 由总上限减去其余段的实际字节决定，至少 3000。
- "test-like 命令"：`run_command` 的命令行匹配 `pytest|runtests|unittest|tox|python -m` 之一。只取 agent 自己看到过的输出，原样截尾。
- 模板里出现的所有文字（包括包装句）在冻结前提交，不再改。
- 渲染失败、任何段缺失源文件时报错，不准静默写成空记录。53 份里有 11 次没改非测试源码，它们的 "Files changed" 写 none，这不是空记录。

**为什么放可见测试输出：** 那是 agent 第一次自己跑出来、自己看到过的内容，不来自 grader。A5 隔离保证 clean 镜像里没有 test patch，所以这部分不含隐藏测试。泄漏检查仍然要覆盖它。

## 4. 泄漏检查（CHECKPOINT A6-1 的核心）

脚本在 host 侧读私有材料（`runs/sprint5-main-private/` 和校准 JSON），**只输出计数和命中位置，不打印私有内容**。对 53 份记录逐份检查：

1. F2P、P2P 的 node id（及其中的测试函数名，长度 ≥ 8 的）是否出现；
2. test patch 里新增的行（去空白后长度 ≥ 20）是否出现；
3. test patch 新建的文件路径是否出现；
4. gold patch 新增的行（去空白后长度 ≥ 20）是否出现。这一项**只报告不阻断**：第一次尝试改对了部分细节是 agent 自己的产出，不是泄漏。但要在 CHECKPOINT 里列出每份的命中数，审计决定是否保留。

1–3 任何命中都阻断，写进 CHECKPOINT 等审计。

另外把 53 份记录全部渲染到 `docs/sprint/a6-attempts/<task>__<first>.txt`，供审计逐份读。汇总清单 `docs/sprint/a6-attempts.json`：每份的 task、first、字节数、各段字节数、sha256、泄漏检查计数。清单本身的 `handoff_sha256` 写进 CHECKPOINT。

## 5. harness 侧步骤

### A6-1：实现（零模型调用）

1. `scripts/run_swe_task.py::run_task` 加关键字参数 `prompt_suffix: str | None = None`，非空时追加在 `public_issue(task)` 之后（中间一个空行）；`prompt_sha256` 按最终 prompt 计算。summary 新增 `retry` 字段：`{arm, first, attempt_sha256}`（B0 路径不写这个字段）。测试：默认参数下 A5 dev 题的 `prompt_sha256` 与改动前一致。
2. `scripts/build_a6_attempts.py`：第 1 节的选取规则 + 第 3 节的渲染 + 第 4 节的检查，写出 `docs/sprint/a6-attempts/` 和 `a6-attempts.json`。确定性：跑两次输出字节相同（测试）。
3. `scripts/run_a6_retry.py`：复用 `run_a5_main.py` 的 `materialize_runner_task`、`retire_infra`、`spent`、`fault_alarm` 等函数，**不改 `run_a5_main.py`**。槽位、打乱、停止条件按第 1 节。R1 运行前从清单读记录并核对 sha；R1 运行后从 `events.jsonl` 取第一条 user 消息核对注入一致。infra 重跑规则同 A5（目录改名 `.infra<n>`，每槽最多重跑 2 次）。
4. `--preflight`：22 道题的 clean 镜像 digest 存在且与 A5 一致；source-only 校验；grader 校准 id 数一致；53 份记录 sha 与清单一致。零模型调用。
5. mock 端到端：用 `_MockLLM` 跑 4 个槽位（R0、R1 各 2，取不同 repo），输出到 `runs/a6-retry-mock/`，确认 summary 字段、注入核对、报告生成都走通。
6. 全量测试。之前就存在的 `test_one_call_no_summary_private_grading_and_durable_replay` 失败已在 `64bfc48` 处理，现在应全绿；不绿就写明。

**CHECKPOINT-A6-1（停下等审计）**，写 `docs/sprint/CHECKPOINT-A6-1.md`：

- 第一次尝试的复算数（应为 53/22），按题列出 first 编号；
- 53 份记录的字节数分布、各段字节数、截断次数；
- 泄漏检查 1–4 的计数表；
- 至少 3 份记录全文贴进 CHECKPOINT（一份没改源码的、一份用满 40 次的、一份自己提交的）；
- preflight 和 mock 的结果；测试结果；各步提交号。

### A6-2：冻结和 canary（审计通过后）

1. 写 `docs/sprint/A6-R-FREEZE.md`：harness commit、agent 侧 `a6-retry-freeze` 指向的 commit（从 agent 的 CHECKPOINT 读）、`a6-attempts.json` 的 sha、`b0-v2.yaml` sha、`main-targets.yaml` sha、`PARALLEL`、`TOTAL_CAP`、打乱种子、模板文字的 sha。
2. 打 tag `a6-retry-freeze`（harness）。之后到正式运行结束，不改 runner、grader、镜像、记录。
3. canary：按打乱后队列的前 4 个槽位里各取 R0、R1 至少 1 个（固定规则：队列顺序中第一个 R0 和第一个 R1 槽位，再加第二个 R0 和第二个 R1），写到正式目录，就是正式运行的一部分。约 2–3 元。
4. 核对：summary 有 `mock: false`、`profile`、`retry`；隔离通过；注入一致；模型名和 base_url 主机记录下来作为后续基准；花费进账本；R0 的 `prompt_sha256` 等于 A5 B0。

**CHECKPOINT-A6-2（停下等审计）**：canary 4 次的 summary 摘要、R1 一份完整的第一条 user 消息全文、模型名、花费。

### A6-3：正式运行（审计通过后）

1. `run_a6_retry.py` 跑剩余槽位，停止条件按第 1 节。
2. 跑完写 `docs/sprint/a6-retry-runs.json`（每槽 summary 的关键字段，schema `a6.retry-runs.v1`），给出 sha，通知 agent 侧。
3. **CHECKPOINT-A6-3（停下）**：槽位完成数 318/318、infra 退役记录、花费、注入一致检查全量结果、停止原因（如有）。**不算 R1−R0，不下结论。**

## 6. coding-agent 侧步骤

### A6-1（与 harness A6-1 并行，零模型调用）

1. `docs/sprint/A6-R-PREREG.zh-CN.md`：把本计划第 1 节原样写入，加上输入文件的 schema 约定（`a6-retry-runs.json` 的字段）。
2. `scripts/analyze_a6_retry.py`：读 `a6-retry-runs.json` 和 harness 的 `a6-attempts.json`，输出主分析和次要指标。diff 重复率需要第二次尝试的 diff，从 harness 运行目录读 `candidate-delta.json`，归一化规则与 harness 构建脚本共用一份实现或逐字节一致的复制（测试比对）。
3. 合成数据：生成三套假数据（真效应 0、+15pp、+30pp），脚本跑出的点估计落在合理范围，置换检验在 0 效应时 p 不显著。写 `docs/sprint/A6-R-SYNTHETIC-REPORT.md`。
4. 提交，打 tag `a6-retry-freeze`（agent 仓库）。写 `docs/sprint/CHECKPOINT-A6-1.md`：提交号、tag、合成数据结果。停下。

### A6-4（收到 harness 的 `a6-retry-runs.json` 之后）

1. 核对 sha 与 harness CHECKPOINT-A6-3 一致。
2. 不改脚本，直接运行，生成 `docs/sprint/A6-R-RESULTS.zh-CN.md`。数字从脚本输出复制。
3. 脚本如果有 bug 必须改，单独提交，写明改了什么、为什么，旧输出保留。
4. 写 CHECKPOINT-A6-4，停下等审计。最终叙述（和 A5 合在一起讲）由审计侧另写，不在本轮。

## 7. 硬约束（两边都适用）

- 不改、不移动 A5 的任何运行目录、交接文件、报告和 tag。只读 `runs/a5-main/`。
- 密钥不进 git、日志或打印。gold、test patch、F2P/P2P 不进入 agent 可见范围；host 侧检查脚本只输出计数。
- 小步提交，不 force push，不 push 到远端（除非用户另外要求），不删除旧证据。
- harness agent 不改 coding-agent 仓库，反之亦然。
- 冻结后的任何代码改动单独提交，写明影响了哪些已完成的运行。
- 不要因为看到 canary 或中途结果就调整模板、槽位或停止条件。

## 8. 时间和花费

| 轮 | 内容 | 人天 | 模型花费 |
| --- | --- | --- | --- |
| A6-1 | 实现、泄漏检查、预注册、合成数据 | 1.5–2 | 0 |
| A6-2 | 冻结、canary | 0.5 | 约 3 元 |
| A6-3 | 318 次，约 5.5 小时墙钟 | 0.5 | 约 172 元 |
| A6-4 | 分析、结果 | 0.5–1 | 0 |
| 合计 | | 约 4 | 上限 210 元 |
