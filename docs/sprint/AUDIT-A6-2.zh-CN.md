# 审计：A6-2（冻结和 canary）

日期：2026-10-13。审计对象：harness `79dc5aa`，内容是 `A6-R-FREEZE.md` 和 `CHECKPOINT-A6-2.md`。

**结论：通过，可以进入 A6-3 正式运行。**

## 审计核对过的内容

- tag `a6-retry-freeze` 指向 `0cbc63d`；`a6-retry-freeze..HEAD` 之间 `scripts/`、`src/`、`configs/` 没有任何改动，所以 canary 运行时的代码就是冻结时的代码。
- agent 侧 `a6-retry-freeze-r2` 指向 `6c67739`，和冻结记录一致。
- 冻结记录里 `b0-v2.yaml`、`main-targets.yaml` 的 sha 写明与 A5 冻结记录相同，审计没有重新计算。
- 4 份 canary summary（审计自己读的）：模型 4/4 都是 `deepseek-flash` @ `api.deepseek.com`；`answer_isolation_pass` 4/4 为真；`retry.arm` 和槽位一致；花费 0.721 / 0.148 / 0.834 / 0.747，合计 2.450，单次都低于 1.5 元。
- R1 第一条 user 消息全文（django-15022）：A5 的 prompt、空一行、然后是记录全文，包装句和模板一致，没有 gold 或测试内容。

## 一个需要记录、但不改设计的现象

sphinx-7590 r0（R0 组，没有注入记录）的停止原因是 `context_overflow`：第 18 步时输入达到 87,823 个 token，上下文窗口是 96,000。A5 的 392 次运行里一次都没出现过这种停止原因，A5 的峰值输入大约在 40–50k。

- 这次是 R0，和注入的记录无关。runner 把它当作有效的失败运行，不是 infra_error。这和 A5 的口径一致，冻结后不改。
- R1 的 prompt 最多多出约 8 KB（大约 2k token），理论上会略微提高溢出的概率。所以 A6-3 的 CHECKPOINT 要按组报告 `context_overflow` 的次数，只描述，不进入主分析，也不作为停止条件。

## A6-3 的补充要求

1. 续跑 `python scripts/run_a6_retry.py`（不带参数），跳过已完成的 4 个 canary 槽位，跑剩下的 314 个。
2. 预计墙钟约 5–6 小时。开跑前关闭系统睡眠，确认 Docker Desktop 在线。
3. 中断的处理：如果进程被中断，或者 Docker 停了，导致出现没有 `summary.json` 的槽位目录，runner 会拒绝续跑。这种情况下**不要删除或移动这些目录**，先停下，写 CHECKPOINT，等审计决定怎么处理。
4. 跑完以后，runner 会自动写出 `docs/sprint/a6-retry-runs.json`。如果没有自动写出，用 `--runs-file` 重写，并在 CHECKPOINT 里说明原因。
5. CHECKPOINT-A6-3 要写：
   - 槽位完成数（应为 318/318）；
   - infra 退役记录；
   - 每组的 status 和 stop_reason 分布，其中包括 `context_overflow`；
   - 注入核对的全量结果；
   - 模型身份是否一致；
   - 累计花费，以及单次最高花费；
   - 停止原因（如果有）；
   - `a6-retry-runs.json` 的 `handoff_sha256`。
6. **不要计算 R1−R0，不要按组汇总解出率，不要下结论。** 只有每组 status 分布会间接带出解出数，这一项可以写，但不要解读。
