# CHECKPOINT-A6-3：正式运行（coding-harness）

日期：2026-10-14。依据：`A6-R-PLAN.zh-CN.md` 第 5 节 A6-3、`AUDIT-A6-2.zh-CN.md` 第 3 节。

**结果：** 318/318 个槽位都已完成，有 summary，没有中断目录。runner 没有触发任何冻结记录里的停止条件，并自动写出了 `a6-retry-runs.json`。但在运行的最后约 4 分钟，DeepSeek 账户余额耗尽，provider 返回 `HTTP 402 Insufficient Balance`。受影响的 22 次运行（R0 8 次、R1 14 次）被记成了普通的 `model_parse_error` 失败，不是 infra_error，所以停止条件没有拦住。**这 22 行还留在 runs 文件里，文件暂不交给 agent 侧，等审计决定。** 冻结后没有改代码，没有删除或移动任何目录。按要求没有计算 R1−R0，没有按组汇总解出率，不下结论。

## 提交

| 提交 | 内容 |
| --- | --- |
| `50f54a7` | `AUDIT-A6-2.zh-CN.md` 和 `A6-R-START-PROMPTS.zh-CN.md` 原样入库 |
| `a15696f` | `docs/sprint/a6-retry-runs.json`（runner 自动写出的，原样提交） |
| 本提交 | 本 CHECKPOINT 和 PROGRESS |

`a6-retry-freeze..HEAD` 之间，`scripts/`、`src/`、`configs/` 没有改动。

## 运行过程

- 开跑前：把系统待机超时从"接电源 7200 秒、电池 900 秒"改成 0（不睡眠），休眠本来就是 0；Docker Desktop 29.8.2 在线，没有残留容器；`runs/a6-retry/` 里只有 4 个 canary 目录，都有 summary。跑完后，待机超时恢复为原值。
- `python scripts/run_a6_retry.py`（不带参数），22:04 开始，次日 03:51 结束，用时约 5 小时 47 分钟。canary 的 4 个槽位按已完成跳过，实际启动 314 次（R0 157、R1 157）。
- runner 报告 `runs/a6-retry/main-report.json`：`halt_reason` 为 null，`not_started` 为 0，`injection_verified_runs` 为 318，`infra_kept` 为空。

## 槽位完成数

318/318。每组 159 个槽位，都有 `summary.json`。没有 summary 的目录：0 个。

## infra 退役记录

7 次，都是 `candidate snapshot failed: container_gone_before_snapshot`。每次都改名为 `.infra1`，重跑一次就完成了，没有槽位用到第 2 次重跑。7 次占全部 325 次尝试的 2.2%，低于 10% 的停止线。

| 退役目录 | 花费（元） |
| --- | --- |
| django__django-15973/r0/b0r1/r3.infra1 | 0.038 |
| pytest-dev__pytest-7324/r1/b0r2/r2.infra1 | 0.074 |
| pytest-dev__pytest-7490/r0/b0r3/r3.infra1 | 0.452 |
| sphinx-doc__sphinx-9461/r1/b0r1/r1.infra1 | 0.303 |
| sphinx-doc__sphinx-9461/r1/b0r1/r3.infra1 | 0.186 |
| sympy__sympy-15599/r0/b0r2/r1.infra1 | 0.474 |
| sympy__sympy-21596/r0/b0r2/r1.infra1 | 0.274 |

## 每组的 status 和 stop_reason 分布

只统计每个槽位最终的那次运行，不含退役的 `.infra1`；受 402 影响的 22 次也算在内。只描述，不解读。

| status | R0 | R1 |
| --- | --- | --- |
| pass | 26 | 19 |
| partial | 32 | 32 |
| fail | 96 | 105 |
| delta_lost | 5 | 3 |
| 合计 | 159 | 159 |

| stop_reason | R0 | R1 |
| --- | --- | --- |
| completed | 68 | 60 |
| max_model_calls | 82 | 73 |
| model_parse_error | 8 | 24 |
| context_overflow | 1 | 2 |
| 合计 | 159 | 159 |

`context_overflow`：R0 1 次（就是 canary 里的 sphinx-7590 r0），R1 2 次。按审计要求只描述，不进入主分析。

`model_parse_error` 里有 22 次是余额耗尽造成的（R0 8、R1 14，见下一节）。另外 10 次发生在 22:22–03:12，都在 R1，调用数 34–39，这几次运行里没有 HTTP 失败的结算记录。

## 余额耗尽（HTTP 402）

日志 `runs/a6-retry-logs/main.out` 的最后部分全是 `LLM call failed: LLM API error 402: Insufficient Balance`。判定方法：看每次运行事件日志里 `model.settled` 的结算记录，找有没有 `note: "http"` 的结算（HTTP 层失败）。318 次里有 22 次有这样的记录，全部集中在 03:47:28–03:51:12，之前的运行一次都没有。

- 3 次是跑到一半遇到 402，失败的是最后一次调用：pytest-dev__pytest-5840/r1/b0r2/r1（第 14 次调用，fail，0.232 元）、sympy__sympy-15599/r1/b0r1/r2（第 37 次，fail，0.789 元）、sympy__sympy-14248/r1/b0r1/r1（第 18 次，partial，0.314 元）。
- 19 次是第一次调用就 402：model_calls 都是 1，候选改动为空，grader 照常评分（17 次 fail，2 次 partial）。每次记账 0.068–0.072 元：结果未知时，CNY 账本按 `unknown_keeps_reserve` 保留预留金额，不是 provider 的实际扣费。19 次合计约 1.33 元。

R0（8 次）：django__django-15022/r0/b0r3/r1、django__django-15973/r0/b0r1/r2、sphinx-doc__sphinx-10614/r0/b0r1/r2、sphinx-doc__sphinx-10614/r0/b0r3/r2、sympy__sympy-13091/r0/b0r3/r3、sympy__sympy-15599/r0/b0r1/r3、sympy__sympy-21596/r0/b0r2/r3、sympy__sympy-21596/r0/b0r3/r1。

R1（14 次）：django__django-13512/r1/b0r1/r1、django__django-15973/r1/b0r2/r2、django__django-15973/r1/b0r3/r3、pytest-dev__pytest-5840/r1/b0r2/r1、scikit-learn__scikit-learn-10908/r1/b0r3/r1、scikit-learn__scikit-learn-12973/r1/b0r1/r3、sphinx-doc__sphinx-8120/r1/b0r3/r3、sympy__sympy-14248/r1/b0r1/r1、sympy__sympy-14248/r1/b0r2/r1、sympy__sympy-15599/r1/b0r1/r2、sympy__sympy-20428/r1/b0r2/r3、sympy__sympy-21596/r1/b0r2/r1、sympy__sympy-21596/r1/b0r3/r2、sympy__sympy-23950/r1/b0r2/r1。

为什么停止条件没拦住：`run_swe_task` 把 provider 的 HTTP 错误算作模型调用失败，以 `model_parse_error` 结束这次运行，status 由 grader 决定。这不属于 `run_infra_reason` 的范围，所以不是 infra_error，也不会退役重跑。冻结记录里的停止条件都没有覆盖"provider 不可用"。累计花费 164.577 元，低于 `TOTAL_CAP` 210 元；用完的是 provider 账户的余额，不是实验的上限。

这次余额耗尽发生在队列最后：按完成时间排序，325 次尝试（318 个槽位加 7 次退役）里，前 303 次没有受影响。但受影响的 22 次在两组之间不均衡（R0 8、R1 14），而且都是没有真正完成的尝试。如果把它们当作有效失败交给分析脚本，会把 provider 故障混进主分析。

**需要审计决定的处理方式（我没有做任何一种）：**

1. 把这 22 次视为 infra（provider 不可用）：充值后，按 A5 的做法改名为 `.infra<n>` 再重跑。按单次平均约 0.5 元估算，约需 11 元，加上已花的 164.577 元仍低于 210 元。这需要审计批准移动目录；或者冻结后单独提交一处代码改动，让 402 这类 provider 错误判为 infra_error，再用现有的续跑逻辑重跑。
2. 保留现状，交给 agent 侧，由分析脚本把这 22 次排除或单列。这需要修订预注册里"有效运行"的口径。
3. 其他方式。

不管选哪种，DeepSeek 账户都要先充值，才能再调用模型。

## 注入核对

- runner：318/318（4 次 canary 加 314 次正式运行；每次运行后核对 `retry`、`prompt_sha256`，以及从 `events.jsonl` 读出的第一条 user 消息全文）。
- 独立复核（`runs/a6-retry-logs/a6_3_stats.py`）：318/318。R0 的消息 sha 等于 A5 B0 的 sha，也等于 summary 里的 sha；R1 的消息拆成 A5 prompt 和记录全文后，两部分都对得上；`retry` 等于期望值；`answer_isolation_pass` 为真；`harness_tool_errors` 为 0。受 402 影响的 22 次也通过了，因为 prompt 在第一次调用之前就已经确定。

## 模型身份

318 个槽位的最终运行都是 `deepseek-flash` @ `api.deepseek.com`，与 canary 相同，没有 `changed_to`。runner 每次运行后都会检查根目录下的全部 summary，包括 7 次退役，没有因为模型身份不同而停下，所以全部 325 次是一致的。

## 花费

| 项 | 元 |
| --- | --- |
| 累计（`runs/a6-retry/` 下全部 summary，含 canary 和 7 次退役） | 164.577 |
| 其中 318 个槽位的最终运行 | 162.776 |
| 单次最高 | 0.940（sympy__sympy-13091/r1/b0r2/r3） |
| 距 `TOTAL_CAP` 210 剩余 | 45.423 |

单次花费都低于账本每次运行 1.000 元的硬上限。

## 停止原因

runner 没有触发停止条件（`halt_reason` 为 null）。实际结束的原因是队列跑完了。provider 余额耗尽不在冻结的停止条件里，见上文。

## `a6-retry-runs.json`

runner 跑完后自动写出：`docs/sprint/a6-retry-runs.json`，`schema` 为 `a6.retry-runs.v1`，`scope` 为 `a6-retry`，`attempts_sha256` 为 `bd932529…`，`slots_expected` 318，`runs` 318 行，每行 `mock: false`。

`handoff_sha256` = `05bea3fb28bd3a7ddb8deac506a1a227c88b0567503a66ec12bce21b1ea46386`

这份文件包含上面那 22 行，**暂不交接**。如果审计选择重跑，重跑后要用 `--runs-file` 重写，sha 会变。

## 下一步

停下等审计决定那 22 次运行怎么处理。没有通知 agent 侧。
