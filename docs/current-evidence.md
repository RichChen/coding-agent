# Current Evidence Summary

> **最后更新**：Batch 6（2026-07-04）。Phase 7.1 实验收口；主结论来自 Batch 5.10 方差检验。

## 1. Deterministic Mechanism Evidence（Phase 6）

来源：`reports/phase6-eval-summary.md`，hard run `20260702_102422`，seeded memory `20260702_102744`。

### Plumbing（`phase6_tiny_24`）

| Config | Success | 说明 |
| --- | ---: | --- |
| A0–A5 | 1.00 | scripted fix 驱动，仅验证管线稳定 |

**结论**：不能用于 skill/memory 机制收益声明。

### Hard mechanism（`phase6_hard_12`，`allow_prefix_scripted_fixes=False`）

| Config | Success | Avg Steps | 主要失败 |
| --- | ---: | ---: | --- |
| A0_baseline | 0.00 | 1.00 | test_failure |
| A1_planner | 0.00 | 6.00 | test_failure |
| A2_multi_agent | 0.00 | 6.00 | test_failure |
| A3_skill | **0.92** | 5.08 | mixed |
| A4_memory | **0.67** | 5.33 | mixed |
| A5_full | **0.97** | 5.03 | success |

**按类别（A3_skill）**：regression/api/traceback 均 1.00；rename 0.67。

### Seeded memory（`--seed-memory`）

| Config | Success | Memory Useful | Memory Stale |
| --- | ---: | ---: | ---: |
| A4_memory | **0.89** | 32 | 1 |
| A5_full | **1.00** | 35 | 0 |

**确定性层结论**：

- Hard baseline 已从饱和降至 0%，满足机制评测前提
- Skill 驱动 deterministic patch 在 hard 任务上有显著收益（0% → 92%）
- Planner / multi-agent 单独不提供 patch strategy（A1/A2 仍为 0%），属诚实负结果
- Seeded memory 可补齐 rename 等边缘 case（A5 达 100%）

**角色**：支撑机制设计合理性；**不是**最终 real LLM 主结论。

---

## 2. Real LLM Evidence — 主结论（Phase 7 medium48）

### 权威：Batch 5.10 方差检验

来源：`reports/llm/20260704_092308/llm-ablation-summary.md`  
`phase7_medium_48` · **48 tasks** · **4 medium repos** · **repeats=2** · seed=42 · Mock=False

| Config | Mean | Std | Repeat 0 | Repeat 1 | Parse Err |
| --- | ---: | ---: | ---: | ---: | ---: |
| L0_llm_single | 45.8% | ±2.1pp | 47.9% | 43.8% | 3 |
| L2_llm_multi | 70.8% | ±2.1pp | 72.9% | 68.8% | 10 |
| **L5_llm_full** | **80.2%** | **±5.2pp** | 75.0% | 85.4% | 10 |

**主结论**：

- L5 mean > L2 mean：**80.2% vs 70.8%**（+9.4pp）
- 两次 repeat 均 L5 ≥ L2
- L5 parse_err 不高于 L2（均为 10 total）
- L5 vs L0：+34.4pp
- 类别增益：skill_heavy +15pp、memory_heavy +12.5pp、multi_file_api +12.5pp、repo_convention +16.7pp
- context_heavy / traceback_repair：mean 持平

详见 `reports/phase7-variance-summary.md`

### Supporting：Batch 5.9 单次 48 题

Run `20260704_062354`，repeats=1：L0=48%，L2=69%，L5=79%，L5−L2=+10.4pp。与 5.10 mean 一致。

详见 `reports/phase7-medium48-summary.md`

### Development history：24-task / probe / hard_12

| 阶段 | Benchmark | 关键结果 | 角色 |
| --- | --- | --- | --- |
| Phase 6 hard_12 | 12 tasks | L2≈92%，L3/L4/L5 < L2 | 暴露 benchmark 饱和与机制负收益，驱动 Phase 7 |
| Probe-12 | 12 tasks | 5.5 未过 gate；5.6 gating 后 L5>L2 | 机制迭代 |
| Full 24 | 24 tasks | 5.8 L5=79%，L5≥L4 | 干扰路由修复 |
| Medium 48 | 48 tasks | 5.9 单次 +10.4pp；**5.10 mean +9.4pp** | **最终主证据** |

旧 tiny/hard eval **不是**主结论。引用时请指向 `phase7_medium_48` + Batch 5.10。

---

## 3. Mechanism Contributions（与主结论对齐）

| 机制 | 证据 |
| --- | --- |
| SkillCard v2 + domain/evidence gating | skill_heavy +15pp；skill_negative_transfer=1；auth domain 已与 memory 同步（Batch 6.0-audit-fix） |
| MemoryHint v2 + holdout matching | memory_heavy +12.5pp（5.4 修复后 0%→86% on probe） |
| Augmentation policy router | 移除 conservative_mix；L5≥L4（5.8） |
| Context expansion + JSON repair | context_heavy L2/L5 均高于 L0；非 L5 主要增益来源 |
| PlanAct + multi-agent | L2=70.8% vs L0=45.8%（+25pp baseline lift） |

Case studies：`docs/case-study-*.md`

---

## 4. Known Limitations

见 `docs/limitations.md`。摘要：

- Synthetic medium repos，非 SWE-bench
- repeats=2，非大规模统计显著性
- L5 run-to-run std 高于 L2
- context_heavy / traceback_repair 非主要增益
- External baselines（OpenHands/SWE-agent/Aider）optional/skip
- **Batch 5.10 主结果在 auth-domain 同步修复前生成**；审计表明该缺口未 materially 改变 overall 结论
- Category 报告按 **primary category** 分桶，任务本身是多标签的
- Memory-enabled configs 为 **online memory**（repeat 内累积，repeat 间隔离）

### Batch 6.0-audit-fix（2026-07-10）

代码与文档修补，**不替换** Batch 5.10 主数字：

1. `TASK_DOMAIN_TAGS` 增加 `auth`，与 memory `DOMAIN_TAGS` 统一
2. `LLMDeveloperAgent` 可读 `tests/` 上下文但**禁止写入** `tests/`
3. 补充 `phase7_medium_48` benchmark 与 domain 一致性单测

---

## 5. Evaluation Contract

三层评测边界见 `docs/evaluation-contract.md`：

1. Fake plumbing — `phase6_tiny_24`（非主结论）
2. Deterministic mechanism — `phase6_hard_12` + A0–A5（机制支撑）
3. **Real LLM mechanism — `phase7_medium_48` + L0/L2/L5**（**主结论**）

---

## 6. Phase 7.1 Acceptance（最终状态）

```text
phase7_medium_48, repeats=2 (Batch 5.10):
L5 mean > L2 mean              ✅ 80.2% vs 70.8%
L5-L2 mean >= +8pp               ✅ +9.4pp
Both repeats L5 >= L2          ✅
L5 parse_err <= L2               ✅ 10 vs 10
L5 mean > L0 + 20pp            ✅ +34.4pp
skill_heavy / memory_heavy L5>L2 ✅
```

**实验收口。** 不再跑真实 LLM eval。
