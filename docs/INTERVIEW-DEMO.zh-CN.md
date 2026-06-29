# 面试讲解稿（A–D 总收口）

> **数字来源**：真实 DeepSeek API（`coding-harness` conda，2026-06-24～27）。  
> **现场演示**：逐步操作见 `docs/DEMO-SCRIPT.zh-CN.md`；路线图见 `docs/SOLID-ROADMAP.zh-CN.md`。

---

## 证据索引

| 主题 | 数字/结论 | 路径 |
|------|-----------|------|
| plan_act 单变量（repo） | baseline 94.4% vs plan_act **100%**，Δ **+5.6%**（12 任务，runs=3） | `reports/examples/baseline_vs_plan_act_permissive_v2_real.md` |
| context compact 效率 | compact_stress 耗时 **-13.6%**、步数 **-0.8**，成功率不回归 | `reports/examples/baseline_vs_context_compact_threshold_real.md` |
| SWE-bench 干净 A/B | baseline **32.0%** vs plan_act **24.0%**，CI 重叠无显著 | `reports/report_20260626T101113.md` |
| SWE-bench scaffold A/B | baseline **20.0%** vs plan_act **26.7%**，CI 重叠无显著 | `reports/report_20260626T194843.md` |
| 污染探针 | 5×重复：池化 exact **54.2%**，**7/10** 多数票定位 | `reports/contamination_probe.md` |
| 多模型矩阵 | v4-pro **96.9%** vs chat **87.5%**（repo 16，runs=2） | `reports/report_20260627T033945.md` |
| 失败 taxonomy | step_limit **47.5%**、none(judge 挂) **38.4%** | `reports/examples/failure_taxonomy.md` |
| plan-act trace | `plan_created` → `plan_updated` → `plan_replanned` | `docs/examples/plan_act_events_redacted.jsonl` |
| 批次 CLOSEOUT | A–D 执行证据 | `docs/changes/SOLID-*-CLOSEOUT.zh-CN.md` |

---

## 30 秒版

这是一个 **可控、可观测、可评测** 的单 Agent Coding Harness。我把评测从 toy 任务扩到 **repo 级** 直至 **SWE-bench Lite 子集**，并用同一套 eval 做单变量 A/B。

三个数字：**plan_act +5.6%**（repo，机制有效）、**compact -13.6% 耗时**（stress，效率正收益）、**污染探针 54.2% + SWE-bench planner null**（评估有效性——最强亮点，不是刷分）。

---

## 2 分钟版

**主线**：模型不可信 → harness 约束工具 → JSONL trace → 离线 eval 量化策略。

1. **架构**：`loop.py` + `runner.py` + `tracing/logger.py` + YAML config  
2. **现场**：`scripts/run_single.py` + `plan_act_permissive.yaml`（详见 DEMO-SCRIPT Step 2–3）  
3. **报告**：`report_20260626T101113.md`（SWE-bench CI + Significance）+ `failure_taxonomy.md`  
4. **收束**：D-1 污染叙事（下方专节）

---

## 能力矩阵（A–D）

| 批次 | 能力 | 一句话 | 证据 |
|------|------|--------|------|
| A | 单变量 plan_act A/B | 同策略下 planner **+5.6%**（repo 12） | `reports/examples/baseline_vs_plan_act_permissive_v2_real.md` |
| A | plan 刷新进 messages | 每步 `plan_updated` 回写对话 | `src/runtime/loop.py` |
| B | suggested_tools + replan | 结构化推进与一次重规划 | `src/runtime/planner.py` |
| B | argv 命令白名单 | 结构化执行 + 精确前缀 | `configs/hardened_argv.yaml` |
| C | token 阈值 compact | stress 集 **-13.6% 耗时**，成功率不回归 | `reports/examples/baseline_vs_context_compact_threshold_real.md` |
| C | bootstrap CI / cost / pass matrix | 多 run 统计 + 显著性一句 | `src/eval/report.py` |
| D | SWE-bench 子集 + 防作弊 | 10 任务 / 3 repo；判定前 restore 测试文件 | `docs/changes/SOLID-D1-SCAFFOLD-CLOSEOUT.zh-CN.md` |
| D | 污染探针 + NOTES | 54.2% 无上下文定位；绝对率不作能力指标 | `reports/contamination_probe.md` · `docs/CONTAMINATION-NOTES.zh-CN.md` |
| D | 失败 taxonomy | 从 CSV 自动聚合 step_limit / judge 挂 | `reports/examples/failure_taxonomy.md` |
| D | 多模型矩阵 | 同 harness 换 model：96.9% vs 87.5% | `reports/report_20260627T033945.md` |

---

## 三个数字亮点（勿混用层级）

| 亮点 | 数字 | 层级 | 说明 |
|------|------|------|------|
| **Planner 机制** | **+5.6%** | repo 自造 12 任务 | 单变量 `plan_act_permissive`，**不是** SWE-bench 结论 |
| **Compact 效率** | **-13.6%** 耗时 | compact_stress | 步数 -0.8，成功率不回归 |
| **评估有效性** | 探针 **54.2%** + SWE-bench **null** | 外部基准 | 强污染 + planner CI 重叠；**最强叙事**，非成功率刷分 |

---

## D-1：外部基准 + 污染方法论（最强亮点）

> 证据：`reports/report_20260626T101113.md`、`reports/contamination_probe.md`、`reports/report_20260626T194843.md`、`docs/CONTAMINATION-NOTES.zh-CN.md`。

**四步叙事：**

1. **接外部基准**：SWE-bench Lite **10 任务 / 3 repo**；可移植 env、题面清洗、gold 仅 `.oracle/`。  
2. **干净单变量 A/B**：baseline vs plan_act_permissive → **32% vs 24%**（runs=5），**CI 重叠、无显著**。  
3. **污染探针**：双峰通过率 + 无 repo 结构文件定位 → **池化 exact 54.2%**、**7/10** 多数票 = instance 记忆；绝对成功率**不作能力指标**。  
4. **防作弊 + scaffold 扩张**：开 `run_command`/`edit_file`、预算 30→40；重跑 **20% vs 27%**（runs=3），**仍无显著**；步数 ~22→~35，瓶颈是真实难度 + 污染，非配置饥饿。

**收口句**：

> 结论不是「agent 多强」，而是「在此数据条件下 planner 相对收益不可辨识——污染压缩了区分度」；治本路径 SWE-bench-Live / held-out（见 CONTAMINATION-NOTES §5）。

---

## 工程深度点

- **argv / CommandPolicy**：`src/policy/rules.py` · `configs/hardened_argv.yaml`  
- **LLMErrorKind → RetryPolicy**：`src/runtime/retry.py`  
- **cancel token + HTTP retry 细分**：`src/runtime/loop.py`  
- **`--cost-per-1k` 成本列**：`scripts/run_eval.py` · `src/eval/report.py`  
- **`is_degenerate_run` 402 免疫**：`src/eval/metrics.py` · 报告 Anomalous Runs  
- **判定前 `_restore_protected_paths`**：`src/eval/runner.py`（防改测试假通过）

---

## 失败与 flaky

- 自动聚合：`reports/examples/failure_taxonomy.md`（step_limit 47.5%、judge 挂 38.4%）  
- 手工叙事示例：`docs/FAILURE-CASES.zh-CN.md`  
- Unstable Tasks：多 config 报告含 Config 列（`src/eval/report.py`）

---

## 历史实验（参考，非三亮点）

| 实验 | 结果 | 路径 |
|------|------|------|
| baseline vs hardened（repo ×3） | 95.8% vs 87.5% | `reports/examples/baseline_vs_hardened_real.md` |
| mini compact | 88.9% vs 91.7% | 早期 mini eval |
| subagent_readonly | 77.8%（7/9） | repo 任务 |

勿与 SWE-bench 数字并列当作「agent 很强」。

---

## 该怎么收束

> 我做的是 **能约束、能度量、能回归** 的 Agent 工程框架；A–C 用 repo 数字证明机制与效率；**D-1 证明我会质疑评测**——污染探针、诚实 null、防作弊、排除 confound。

---

## 若被追问「还缺什么」

- **已 defer**：真 SSE、L2 摘要、多 worker、LLM planner、Docker 隔离（`docs/changes/CODEX-DEFERRED-GAPS.zh-CN.md`）  
- **评测治本**：SWE-bench-Live / post-cutoff held-out（`docs/CONTAMINATION-NOTES.zh-CN.md`）  
- **演示**：`docs/DEMO-SCRIPT.zh-CN.md` · **全景**：`docs/SOLID-ROADMAP.zh-CN.md`
