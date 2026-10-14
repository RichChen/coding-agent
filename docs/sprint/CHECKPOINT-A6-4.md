# CHECKPOINT-A6-4（coding-agent 侧）

日期：2026-10-14。依据 harness `docs/sprint/AUDIT-A6-3.zh-CN.md` 第 3 节，执行 `A6-R-PLAN.zh-CN.md` 第 6 节的 A6-4。

脚本没有报 STOP，没有发现 bug，分析脚本、预注册和结论口径都没有改。没有 push。没有改 coding-harness。没有调用模型，花费 0。

## 主分析结论

结论原文（脚本输出，未改）：

> 未检出大于 15.9 个百分点的效应（2.8×s/√N）；95% 区间上限 3.8 个百分点。点估计 -6.6 个百分点，95% 区间 -17.7 到 3.8

| 项 | 值 |
| --- | --- |
| 题数 N | 22（剔除：无） |
| 点估计（平均 d_t，R1 − R0） | -0.0657 |
| 双侧符号翻转 p | 0.2880 |
| 95% 区间（按题 bootstrap） | -0.1768 到 0.0379 |
| s_obs（d_t 样本标准差） | 0.2660 |
| X（2.8×s_obs/√N） | 15.9 个百分点 |
| 95% 区间上限 | 3.8 个百分点 |

第二阶段判定（脚本输出原文）：第二阶段触发（点估计 ≥ +5pp 且区间含 0）：不满足，不做第二阶段

## 次要指标（描述性，不做检验，不进结论句）

只算进入主分析的题的有效运行，每组 159 次。

| 指标 | R0 | R1 |
| --- | --- | --- |
| 1. diff 重复率 | 29/159（0.182） | 44/159（0.277） |
| 2. 文件复用 | 104/159（0.654） | 111/159（0.698） |
| 3. first_edit_step | 平均 15.367，中位数 12.0，null 20 次 | 平均 16.376，中位数 12.0，null 18 次 |
| 4. model_calls | 平均 31.377，用满 40 次 89/159（0.560） | 平均 32.082，用满 40 次 87/159（0.547） |
| 5. 花费 CNY | 平均 0.497 | 平均 0.589 |

按 A5 B0 档位（只描述，不作为效应证据）：0/3 档 13 题，平均 d_t -0.0085；中间档 9 题，平均 d_t -0.1481。

## 运行的命令

在 `D:\crq\src\coding-agent` 下运行，系统 Python：

```
python scripts/analyze_a6_retry.py --runs D:\crq\src\coding-harness\docs\sprint\a6-retry-runs.json --attempts D:\crq\src\coding-harness\docs\sprint\a6-attempts.json --harness-root D:\crq\src\coding-harness --out docs/sprint/A6-R-ANALYSIS-OUTPUT.zh-CN.md --expect-runs-sha a0870f766a3b02f6ce34d6e5291ae59f8ab5160f46ae6e7671f3fd39f08a4256 --expect-attempts-sha bd93252922c990ec61071caecb5a6bf5e604202cbbcf30d296f2b875794dd3ce
```

退出码 0。写 CHECKPOINT 前，用同一条命令（只把 `--out` 换成临时文件）又跑了一次，输出和已提交的 `A6-R-ANALYSIS-OUTPUT.zh-CN.md` 逐字节相同（SHA-256 `16bfaffc…f682`），临时文件已删除。

## 两个期望 sha 的核对

| 文件 | 期望 | 实际 handoff_sha256 | 结果 |
| --- | --- | --- | --- |
| `a6-retry-runs.json` | `a0870f766a3b02f6ce34d6e5291ae59f8ab5160f46ae6e7671f3fd39f08a4256` | 同左 | 一致，没有 `runs_sha_unexpected` |
| `a6-attempts.json` | `bd93252922c990ec61071caecb5a6bf5e604202cbbcf30d296f2b875794dd3ce` | 同左 | 一致，没有 `attempts_sha_unexpected` |

runs 里记录的 `attempts_sha256` 也是 `bd932529…`，和清单一致，没有 `attempts_sha_mismatch`。输入核对全部为"无"：第一次尝试 53 次、22 道题，槽位 318 行，infra_error 0 次。

两个输入文件在 harness 里都已提交，工作区没有改动；runs 文件最后一次提交是 `087babd`（harness HEAD `539af1b`）。

## 用的是哪个版本的脚本

运行时 HEAD 上的 `scripts/` 和 tag `a6-retry-freeze-r2`（`6c67739e8816621826493d9ef4ca4da64508ac37`）没有差异：`git diff --stat a6-retry-freeze-r2 0a81fca -- scripts` 为空，工作区也没有改动。之后 `scripts/` 下只新增了 `describe_a6_stops.py`；`analyze_a6_retry.py`、`a6_diff.py`、`handoff_sha.py` 和 tag 上的一样。

## 提交

| 提交 | 内容 |
| --- | --- |
| `0a81fca` | 冻结脚本的原样输出 `A6-R-ANALYSIS-OUTPUT.zh-CN.md` |
| `1f72992` | 非预注册描述的计算脚本 `scripts/describe_a6_stops.py`、测试 `tests/test_describe_a6_stops.py`，以及输出 `A6-R-STOP-DESCRIPTION.zh-CN.md` |
| `1f3287e` | `A6-R-RESULTS.zh-CN.md`：前半部分和脚本输出逐字节相同，后接"偏差（非脚本生成）"和"非预注册的描述（非脚本生成）"两节 |
| 本提交 | 本 CHECKPOINT |

描述脚本的命令：

```
python scripts/describe_a6_stops.py --runs D:\crq\src\coding-harness\docs\sprint\a6-retry-runs.json --retired D:\crq\src\coding-harness\runs\a6-retry-logs\provider402-retired.json --out docs/sprint/A6-R-STOP-DESCRIPTION.zh-CN.md
```

测试：`python -m pytest -q -p no:cacheprovider tests/test_analyze_a6_retry.py tests/test_a6_diff.py tests/test_describe_a6_stops.py`，40 passed。

## 请审计注意

1. **parse_error 里 partial 的次数。** 审计第 2 节写 11 次 `model_parse_error` 中"3 次是 partial"，runs 文件里是 4 次：sympy__sympy-13091/r1/b0r2/r2、sympy__sympy-13091/r1/b0r3/r1、sympy__sympy-14248/r1/b0r2/r1、sympy__sympy-14248/r1/b0r2/r3。差的那一次可能是重跑的 sympy__sympy-14248/r1/b0r2/r1。结果报告以 runs 文件为准，并写明了这个差异。
2. **"用满 40 次"和 `max_model_calls` 不是同一个量。** 次要指标 4 按 `model_calls ≥ 40` 计（R0 89、R1 87），stop_reason 为 `max_model_calls` 的是 R0 87、R1 79。差额是用满 40 次调用、但 stop_reason 是 completed（R0 2、R1 7）或 context_overflow（R1 1）的运行。结果报告的描述一节写了这一点。
3. **偏差一节的事实来源。** 402 的经过、选取规则、`.infra1` / `.infra2` 的处理、作废的 runs 文件（`a15696f`，`05bea3fb…`）和花费（退役目录 2.662 元，累计 178.709 元）都引自 harness `CHECKPOINT-A6-3.md` 和本审计第 1 节，agent 侧没有另外核实。槽位名单是 `describe_a6_stops.py` 从 `provider402-retired.json` 读出来的，和 harness CHECKPOINT 列的一致（R0 8 个，R1 14 个）。
4. `docs/memory-v2/` 是之前就有的未跟踪目录，没有动，也没有提交。

最终叙述（和 A5 合在一起讲）由审计来写。停下等审计。
