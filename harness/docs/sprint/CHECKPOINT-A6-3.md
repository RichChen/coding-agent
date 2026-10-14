# CHECKPOINT-A6-3：正式运行（coding-harness）

日期：2026-10-14。依据：`A6-R-PLAN.zh-CN.md` 第 5 节 A6-3、`AUDIT-A6-2.zh-CN.md` 第 3 节。

**结果：** 318/318 个槽位都已完成，有 summary，没有中断目录。第一轮跑到最后约 4 分钟时，DeepSeek 账户余额耗尽，22 次运行（R0 8、R1 14）被 `HTTP 402 Insufficient Balance` 截断。用户充值并同意后，这 22 次按 A5 的 infra 做法退役为 `.infra1` 并重跑。重跑后 318 个槽位的最终运行里，没有一次带 HTTP 失败的结算记录。`a6-retry-runs.json` 已用 `--runs-file` 重写，可以交接。冻结后没有改代码，没有删除任何目录。按要求没有计算 R1−R0，没有按组汇总解出率，不下结论。

## 提交

| 提交 | 内容 |
| --- | --- |
| `50f54a7` | `AUDIT-A6-2.zh-CN.md` 和 `A6-R-START-PROMPTS.zh-CN.md` 原样入库 |
| `a15696f` | 第一轮跑完时 runner 自动写出的 `a6-retry-runs.json`（含 22 行 402，已作废） |
| `9f22521` | 第一版 CHECKPOINT-A6-3 和 PROGRESS（停下等决定） |
| `087babd` | 重跑后用 `--runs-file` 重写的 `a6-retry-runs.json` |
| 本提交 | 本 CHECKPOINT 的重跑更新和 PROGRESS |

`a6-retry-freeze..HEAD` 之间，`scripts/`、`src/`、`configs/` 没有改动。

## 运行过程

- 开跑前：把系统待机超时从"接电源 7200 秒、电池 900 秒"改成 0（不睡眠），休眠本来就是 0；Docker Desktop 29.8.2 在线，没有残留容器；`runs/a6-retry/` 里只有 4 个 canary 目录，都有 summary。
- 第一轮：`python scripts/run_a6_retry.py`（不带参数），22:04 开始，次日 03:51 结束，用时约 5 小时 47 分钟。canary 的 4 个槽位按已完成跳过，实际启动 314 次（R0 157、R1 157）。runner 报告 `runs/a6-retry/main-report.json`：`halt_reason` 为 null，`not_started` 为 0，`injection_verified_runs` 为 318，`infra_kept` 为空。最后 22 次被 402 截断，见下文。
- 重跑（11:04–11:47）：详见"余额耗尽后的重跑"一节。重跑一直用 `--slot`，所以第一轮的 `main-report.json` 没有被覆盖。
- 全部跑完后，待机超时恢复为原值（7200 秒 / 900 秒）。

## 余额耗尽（HTTP 402）

日志 `runs/a6-retry-logs/main.out` 的最后部分全是 `LLM call failed: LLM API error 402: Insufficient Balance`。判定方法：看每次运行事件日志里 `model.settled` 的结算记录，找有没有 `note: "http"` 的结算（HTTP 层失败）。第一轮 318 次最终运行里有 22 次有这样的记录，全部集中在 03:47:28–03:51:12，之前的运行一次都没有。

- 3 次是跑到一半遇到 402，失败的是最后一次调用：pytest-dev__pytest-5840/r1/b0r2/r1（第 14 次调用）、sympy__sympy-15599/r1/b0r1/r2（第 37 次）、sympy__sympy-14248/r1/b0r1/r1（第 18 次）。
- 19 次是第一次调用就 402：model_calls 都是 1，候选改动为空，grader 照常评分。每次记账 0.068–0.072 元：结果未知时，CNY 账本按 `unknown_keeps_reserve` 保留预留金额，不是 provider 的实际扣费。

R0（8 次）：django__django-15022/r0/b0r3/r1、django__django-15973/r0/b0r1/r2、sphinx-doc__sphinx-10614/r0/b0r1/r2、sphinx-doc__sphinx-10614/r0/b0r3/r2、sympy__sympy-13091/r0/b0r3/r3、sympy__sympy-15599/r0/b0r1/r3、sympy__sympy-21596/r0/b0r2/r3、sympy__sympy-21596/r0/b0r3/r1。

R1（14 次）：django__django-13512/r1/b0r1/r1、django__django-15973/r1/b0r2/r2、django__django-15973/r1/b0r3/r3、pytest-dev__pytest-5840/r1/b0r2/r1、scikit-learn__scikit-learn-10908/r1/b0r3/r1、scikit-learn__scikit-learn-12973/r1/b0r1/r3、sphinx-doc__sphinx-8120/r1/b0r3/r3、sympy__sympy-14248/r1/b0r1/r1、sympy__sympy-14248/r1/b0r2/r1、sympy__sympy-15599/r1/b0r1/r2、sympy__sympy-20428/r1/b0r2/r3、sympy__sympy-21596/r1/b0r2/r1、sympy__sympy-21596/r1/b0r3/r2、sympy__sympy-23950/r1/b0r2/r1。

为什么停止条件没拦住：`run_swe_task` 把 provider 的 HTTP 错误算作模型调用失败，以 `model_parse_error` 结束这次运行，status 由 grader 决定。这不属于 `run_infra_reason` 的范围，所以不是 infra_error，也不会退役重跑。冻结记录里的停止条件都没有覆盖"provider 不可用"。

## 余额耗尽后的重跑

用户充值后要求"重新运行受影响的部分，把这轮做好"，相当于第一版 CHECKPOINT 里的选项 1，走的是移动目录的路线，没有改代码。

1. **退役。** 用不入库的辅助脚本 `runs/a6-retry-logs/retire_402.py` 找出"最终运行带 `note: "http"` 结算"的槽位，断言恰好 22 个、且每个槽位都还有 infra 重跑额度，然后对每个调用 `run_a5_main.retire_infra(run_dir)`，也就是 A5 和本轮 runner 退役 infra 用的同一个函数。22 个目录都改名为 `.infra1`，原样保留，没有删除。对应关系记录在 `runs/a6-retry-logs/provider402-retired.json`。这 22 个退役目录的 summary 没有改动，status 仍是 grader 给的值，不是 `infra_error`。
2. **单槽位试跑。** `python scripts/run_a6_retry.py --slot sympy__sympy-15599/r1/b0r1/r2`，11:10 完成。跑满 40 次调用，没有 402，花费 0.727 元，`halt_reason` 为 null。报告另存为 `runs/a6-retry-logs/rerun-1-slots-report.json`。
3. **其余 21 个。** 按原队列顺序（`runs/a6-retry-logs/rerun-slots.txt`）用 21 个 `--slot` 参数一次跑完，11:10:38 开始，11:47 结束，退出码 0。报告：`halt_reason` 为 null，`started` 21，`injection_verified_runs` 318。报告另存为 `runs/a6-retry-logs/rerun-2-slots-report.json`，日志是 `runs/a6-retry-logs/rerun-2.out`，里面没有 402。
4. **重跑中的 infra。** 有 2 次 `container_gone_before_snapshot`，与第一轮那 7 次原因相同：sphinx-doc__sphinx-10614/r0/b0r3/r2 和 sympy__sympy-15599/r0/b0r1/r3。runner 把它们改名为 `.infra2`，再重跑一次就完成了。这两个槽位因此用满了 2 次 infra 额度（`.infra1` 是 402，`.infra2` 是容器丢失）。

重跑没有看 solved，也没有挑选槽位：22 个槽位由 HTTP 结算记录机械地确定，一个不多，一个不少。

## 槽位完成数

318/318。每组 159 个槽位，都有 `summary.json`。`runs/a6-retry/` 下共 349 个运行目录（318 个最终运行，加上 31 个退役），都有 summary，没有中断目录。

## infra 退役记录

共 31 个退役目录：

- **9 次真正的 infra_error**，都是 `candidate snapshot failed: container_gone_before_snapshot`：第一轮 7 次，重跑中 2 次。
- **22 次 provider 402**，由重跑前的人工退役产生，summary 里的 status 不是 infra_error。

runner 的 10% 停止线按 status==infra_error 计数：9/349 = 2.6%。即使把 22 次 402 也算进去，31/349 = 8.9%，仍低于 10%。

| 退役目录 | 原因 | 花费（元） |
| --- | --- | --- |
| django__django-15973/r0/b0r1/r3.infra1 | 容器丢失 | 0.038 |
| pytest-dev__pytest-7324/r1/b0r2/r2.infra1 | 容器丢失 | 0.074 |
| pytest-dev__pytest-7490/r0/b0r3/r3.infra1 | 容器丢失 | 0.452 |
| sphinx-doc__sphinx-9461/r1/b0r1/r1.infra1 | 容器丢失 | 0.303 |
| sphinx-doc__sphinx-9461/r1/b0r1/r3.infra1 | 容器丢失 | 0.186 |
| sympy__sympy-15599/r0/b0r2/r1.infra1 | 容器丢失 | 0.474 |
| sympy__sympy-21596/r0/b0r2/r1.infra1 | 容器丢失 | 0.274 |
| sphinx-doc__sphinx-10614/r0/b0r3/r2.infra2 | 容器丢失（重跑中） | 0.821 |
| sympy__sympy-15599/r0/b0r1/r3.infra2 | 容器丢失（重跑中） | 0.653 |
| 上文 22 个槽位的 `.infra1` | provider 402 | 合计 2.662 |

## 每组的 status 和 stop_reason 分布

只统计每个槽位最终的那次运行，不含退役目录。只描述，不解读。括号里是重跑前第一版的数，方便对照。

| status | R0 | R1 |
| --- | --- | --- |
| pass | 27（26） | 20（19） |
| partial | 32（32） | 31（32） |
| fail | 94（96） | 105（105） |
| delta_lost | 6（5） | 3（3） |
| 合计 | 159 | 159 |

| stop_reason | R0 | R1 |
| --- | --- | --- |
| completed | 71（68） | 66（60） |
| max_model_calls | 87（82） | 79（73） |
| model_parse_error | 0（8） | 11（24） |
| context_overflow | 1（1） | 3（2） |
| 合计 | 159 | 159 |

`context_overflow`：R0 1 次（就是 canary 里的 sphinx-7590 r0），R1 3 次。按审计要求只描述，不进入主分析。

`model_parse_error`：第一轮里 R0 的 8 次全部是 402，重跑后 R0 为 0。R1 的 11 次里，10 次是第一轮 22:22–03:12 的运行，1 次是重跑的 sympy__sympy-14248/r1/b0r2/r1（39 次调用）。这 11 次都没有 HTTP 失败的结算记录（`a6_3_stats.py` 的 `http_failure_runs` 两组都是空的）。

## 注入核对

- runner：318/318（4 次 canary、314 次第一轮正式运行，加上 22 次重跑；每次运行后核对 `retry`、`prompt_sha256`，以及从 `events.jsonl` 读出的第一条 user 消息全文）。重跑报告的 `injection_verified_runs` 是 318，说明 runner 重新核对了全部最终运行。
- 独立复核（`runs/a6-retry-logs/a6_3_stats.py`，重跑后重新运行）：318/318。R0 的消息 sha 等于 A5 B0 的 sha，也等于 summary 里的 sha；R1 的消息拆成 A5 prompt 和记录全文后，两部分都对得上；`retry` 等于期望值；`answer_isolation_pass` 为真；`harness_tool_errors` 为 0。

## 模型身份

318 个槽位的最终运行都是 `deepseek-flash` @ `api.deepseek.com`，与 canary 相同，没有 `changed_to`。runner 每次运行后都会检查根目录下的全部 summary（包括退役目录），没有因为模型身份不同而停下，所以 349 次尝试全部一致。

## 花费

| 项 | 元 |
| --- | --- |
| 累计（`runs/a6-retry/` 下全部 summary，含 canary 和 31 个退役目录） | 178.709 |
| 其中第一轮结束时的累计 | 164.577 |
| 其中重跑新增（22 次重跑，加上 2 次 `.infra2`） | 14.132 |
| 其中 318 个槽位的最终运行 | 172.772 |
| 单次最高 | 0.940（sympy__sympy-13091/r1/b0r2/r3，第一轮） |
| 距 `TOTAL_CAP` 210 剩余 | 31.291 |

单次花费都低于账本每次运行 1.000 元的硬上限，也低于 1.5 元的停下线。

## 停止原因

两次运行 runner 都没有触发停止条件（`halt_reason` 均为 null），都是因为队列跑完而结束。provider 余额耗尽不在冻结的停止条件里，已经通过上面的重跑处理掉。

## `a6-retry-runs.json`

重跑后执行 `python scripts/run_a6_retry.py --runs-file` 重写：`docs/sprint/a6-retry-runs.json`，`schema` 为 `a6.retry-runs.v1`，`scope` 为 `a6-retry`，`attempts_sha256` 为 `bd932529…`，`slots_expected` 318，`runs` 318 行，每行 `mock: false`，`run_dir` 互不重复，没有一行指向退役目录。

`handoff_sha256` = `a0870f766a3b02f6ce34d6e5291ae59f8ab5160f46ae6e7671f3fd39f08a4256`

第一版的 sha `05bea3fb…`（提交 `a15696f`）作废，不要使用。

## 下一步

停下，等审计。没有通知 agent 侧。
