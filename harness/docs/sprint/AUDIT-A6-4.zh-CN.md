# 审计：A6-4（agent 侧分析）

日期：2026-10-14。审计对象：coding-agent `1a3d3bf`，包括 `CHECKPOINT-A6-4.md`、`A6-R-ANALYSIS-OUTPUT.zh-CN.md`、`A6-R-RESULTS.zh-CN.md`。

**结论：通过。A6-R 到此结束，不做第二阶段。**

## 审计复核过的

- `git diff a6-retry-freeze-r2 HEAD -- scripts` 只多出 `describe_a6_stops.py`，`analyze_a6_retry.py`、`a6_diff.py` 和 tag 上的版本相同。
- 审计用 CHECKPOINT 里的命令、两个期望 sha，自己重跑了一遍分析脚本：退出码 0，输出 sha256 `16bfaffc…f682`，和已提交的 `A6-R-ANALYSIS-OUTPUT.zh-CN.md` 逐字节相同。
- 主分析：N=22，点估计 −6.6pp，p=0.288，95% 区间 [−17.7, +3.8]，s_obs=0.266，X=15.9pp。第二阶段触发条件（点估计 ≥ +5pp）不满足。
- 结果报告的"偏差"和"非预注册的描述"两节标明了非脚本生成，数字和 harness CHECKPOINT-A6-3、runs 文件一致。

## 对 CHECKPOINT 待决项的回复

1. parse_error 里 partial 是 4 次：以 runs 文件为准，`AUDIT-A6-3` 写的"3 次"是审计数错了。
2. "用满 40 次"和 `max_model_calls` 口径不同：认可结果报告里的说明。
3. 偏差一节引用 harness 的事实：认可。

## 审计另做的事后分析（非预注册，只描述）

脚本是 coding-agent 的 `scripts/posthoc_a6_anchor.py`，复用冻结的 `a6_diff.py`，只读。目的是拆开次要指标 1 的 diff 重复率：

| 量 | R0 | R1 |
| --- | --- | --- |
| 最终 diff 与第一次完全相同 | 29/159 | 44/159 |
| 其中两边都为空 | 9 | 7 |
| 其中第一次非空、且相同 | 20 | 37 |
| 两边都非空时相似度的中位数（difflib ratio） | 0.658 | 0.873 |
| 相似度的上四分位 | 0.857 | 1.000 |
| 相似度 ≥ 0.9 的运行 | 24/115 | 53/118 |
| 其中解出 | 1 | 1 |
| 相似度 < 0.9 的运行中解出 | 19/91 | 14/65 |

R1 更常停在接近第一次尝试的改法上，而这类运行几乎都没有解出。这只是描述，"看了记录 → 锚定 → 失败"的因果关系没有检验。最终报告把它写成机制假设。
