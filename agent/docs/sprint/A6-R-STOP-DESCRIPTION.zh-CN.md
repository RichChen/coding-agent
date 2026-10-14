# A6-R stop_reason 和 status 按组分布（非预注册，描述性）

输入：`a6-retry-runs.json`，handoff_sha256 `a0870f766a3b02f6ce34d6e5291ae59f8ab5160f46ae6e7671f3fd39f08a4256`，318 行。
只读每行的 `stop_reason`、`status`、`model_calls`。不做检验。

## stop_reason

| stop_reason | R0 | R1 |
| --- | --- | --- |
| max_model_calls | 87 | 79 |
| completed | 71 | 66 |
| model_parse_error | 0 | 11 |
| context_overflow | 1 | 3 |
| 合计 | 159 | 159 |

## status

| status | R0 | R1 |
| --- | --- | --- |
| fail | 94 | 105 |
| partial | 32 | 31 |
| pass | 27 | 20 |
| delta_lost | 6 | 3 |
| 合计 | 159 | 159 |

## stop_reason = model_parse_error 的运行

| 槽位 | 组 | model_calls | 最终 status |
| --- | --- | --- | --- |
| sphinx-doc__sphinx-10614/r1/b0r2/r1 | R1 | 39 | fail |
| sphinx-doc__sphinx-10614/r1/b0r2/r2 | R1 | 39 | fail |
| sphinx-doc__sphinx-10614/r1/b0r2/r3 | R1 | 39 | fail |
| sympy__sympy-13091/r1/b0r2/r2 | R1 | 39 | partial |
| sympy__sympy-13091/r1/b0r2/r3 | R1 | 34 | fail |
| sympy__sympy-13091/r1/b0r3/r1 | R1 | 39 | partial |
| sympy__sympy-13091/r1/b0r3/r3 | R1 | 39 | pass |
| sympy__sympy-14248/r1/b0r2/r1 | R1 | 39 | partial |
| sympy__sympy-14248/r1/b0r2/r3 | R1 | 39 | partial |
| sympy__sympy-15599/r1/b0r3/r2 | R1 | 39 | fail |
| sympy__sympy-20428/r1/b0r1/r2 | R1 | 35 | fail |

## stop_reason = context_overflow 的运行

| 槽位 | 组 | model_calls | 最终 status |
| --- | --- | --- | --- |
| django__django-13964/r1/b0r2/r1 | R1 | 34 | fail |
| pytest-dev__pytest-5840/r1/b0r2/r3 | R1 | 36 | fail |
| sphinx-doc__sphinx-7590/r0/b0r1/r3 | R0 | 18 | fail |
| sphinx-doc__sphinx-8120/r1/b0r3/r3 | R1 | 40 | fail |

## provider 402 退役的槽位

- 退役记录 `provider402-retired.json`：22 个槽位，R0 8 个，R1 14 个。
- R0：django__django-15022/r0/b0r3/r1、django__django-15973/r0/b0r1/r2、sphinx-doc__sphinx-10614/r0/b0r1/r2、sphinx-doc__sphinx-10614/r0/b0r3/r2、sympy__sympy-13091/r0/b0r3/r3、sympy__sympy-15599/r0/b0r1/r3、sympy__sympy-21596/r0/b0r2/r3、sympy__sympy-21596/r0/b0r3/r1
- R1：django__django-13512/r1/b0r1/r1、django__django-15973/r1/b0r2/r2、django__django-15973/r1/b0r3/r3、pytest-dev__pytest-5840/r1/b0r2/r1、scikit-learn__scikit-learn-10908/r1/b0r3/r1、scikit-learn__scikit-learn-12973/r1/b0r1/r3、sphinx-doc__sphinx-8120/r1/b0r3/r3、sympy__sympy-14248/r1/b0r1/r1、sympy__sympy-14248/r1/b0r2/r1、sympy__sympy-15599/r1/b0r1/r2、sympy__sympy-20428/r1/b0r2/r3、sympy__sympy-21596/r1/b0r2/r1、sympy__sympy-21596/r1/b0r3/r2、sympy__sympy-23950/r1/b0r2/r1
