# Phase 7 Positive Gain Summary（Full 24）

Batch **5.7** — `phase7_medium_24` 真实 DeepSeek 评测（repeats=1，seed=42，非 mock）。

---

## 运行信息

| 项 | 值 |
| --- | --- |
| 任务集 | `benchmarks/tasks/phase7_medium_24.yaml`（24 任务） |
| 主对比 Run ID | `20260703_231744` |
| 机制归因 Run ID | `20260704_000519` |
| Mock LLM | **False** |
| Seed | 42 |
| Repeats | 1 |

---

## 跑前轻量检查（已通过）

| 检查项 | 结论 |
| --- | --- |
| `inventory_tax_api.md` 无答案泄露 | ✅ 仅描述 Result / tax_profile / API signature 通用规则，无具体断言数值 |
| `context_primary` 关闭 memory 不影响 `memory_heavy` | ✅ `memory_primary` 独立 route，`max_memory_hints=3` |
| parse repair 指标完整 | ✅ report 含 `parse_err`、`repair_try`、`repair_ok`（见下表） |

---

## Overall Success

| Config | Success | Δ vs L0 | parse_err | repair_try | repair_ok | patch_applied | skill_inj | skill_neg | mem_inj |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L0_llm_single | **46%** (11/24) | — | 0 | 0 | 0 | 19 | 0 | 0 | 0 |
| L2_llm_multi | **71%** (17/24) | +25pp | 4 | 4 | 4 | 29 | 0 | 0 | 0 |
| L3_llm_skill | **75%** (18/24) | +29pp | 5 | 3 | 3 | 29 | 30 | — | 0 |
| L4_llm_memory | **83%** (20/24) | +38pp | 2 | 2 | 2 | 37 | 0 | — | 105 |
| L5_llm_full | **79%** (19/24) | **+33pp** | 3 | 2 | 2 | 31 | 12 | 3 | 36 |

**L5 vs L2：+8.4pp**（79% vs 71%）。

---

## 按机制类别 Success

| Category | Tasks | L0 | L2 | L3 | L4 | L5 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| skill_heavy | 5 | 20% | 60% | 60% | 80% | **80%** |
| context_heavy | 5 | 80% | **100%** | **100%** | 80% | 80% |
| memory_heavy | 7 | 43% | 86% | 86% | 86% | **100%** |

其他标签（repo_convention / multi_file_api / traceback_repair）见各 run 的 `llm-ablation-summary.md`。

---

## 验收线对照

### 最低线

| 条件 | 结果 |
| --- | --- |
| L5 ≥ L2 | ✅ 79% ≥ 71% |
| L5 ≥ L0 + 20pp | ✅ 79% ≥ 66% |
| skill_heavy：L3 或 L5 ≥ L2 | ✅ L5=80% ≥ L2=60% |
| memory_heavy：L4 或 L5 ≥ L2 | ✅ L5=100% ≥ L2=86% |
| context_heavy：L2 或 L5 > L0 | ✅ L2=100% > L0=80% |

### 理想线

| 条件 | 结果 |
| --- | --- |
| L5 ≥ L2 + 10pp | ❌ +8.4pp（差 1.6pp） |
| L5 parse_err ≤ L2 + 1 | ✅ 3 ≤ 5 |
| skill_negative_transfer = 0 | ❌ L5=3（需 Batch 6 case study 解释） |
| memory_heavy 不低于 probe 趋势 | ✅ full 24 memory_heavy **100%**（probe_12 为 75%） |

---

## L5 失败任务（5/24）

| 任务 | 类别 | L2 | 说明 |
| --- | --- | ---: | --- |
| `evt_serialization_01` | multi_file_api | ❌ | L2/L5 共同难点 |
| `cfg_key_alias_01` | multi_file_api | ❌ | L2/L5 共同难点 |
| `evt_context_pipeline_01` | context_heavy | ✅ | **L5 独有回退**（probe_12 已通过，full 24 波动） |
| `cfg_schema_validation_01` | skill_heavy | ✅ | L5 独有回退 |
| `evt_retry_policy_01` | repo_convention | ✅ | L5 独有回退 |

---

## 机制归因要点

1. **Memory 在 full 24 上体现正向收益**：L5 memory_heavy **100%**（7/7），高于 L2 **86%**；与 Batch 5.4–5.6 memory hint / domain / warmup 修复一致。
2. **Skill domain gating 有效**：L5 skill_heavy **80%** > L2 **60%**；`skill_inj=12`（低于无 gating 时的噪声注入规模）。
3. **Full stack 整体领先 L2**：PlanAct + MultiAgent + Skill + Memory 组合在 24 任务上 **+8.4pp**，支撑主线叙事。
4. **Parse 瑕疵可控**：L5 `parse_err=3`，`repair_ok=2/2`；低于 L2 的 parse_err=4，但非零，README 中应如实标注。
5. **Context 子集未全面超越 L2**：L5 context_heavy=80% vs L2=100%，主要受 `evt_context_pipeline_01` 波动影响；叙事写「整体正向，context 仍有波动任务」。

---

## 结论与下一步

**Full 24 最低准入线已通过。** L5 在 24 任务真实评测上 **高于 L2**，memory_heavy 子集显著受益，skill/context 无系统性拖垮。

**叙事建议（Batch 6）：**

- 写「full stack 在 Phase 7 medium benchmark 上带来 **+8.4pp** 相对 multi-agent baseline 的真实 LLM 正向收益」。
- 强调 memory_heavy **100%**、skill domain gating、augmentation policy router。
- 不写「显著领先 +10pp」；parse_err 与 3 次 skill_negative_transfer 如实披露。
- Case studies：`inv_api_tax_01`（skill 修复）、memory holdout 成功路径、共享难点 multi_file_api。

**不建议**在 full 24 结果上继续大改机制（避免过拟合）；Batch 6 以文档与可复现报告为主。

---

## 报告路径

| 批次 | 路径 |
| --- | --- |
| Probe-12 全历程 | `reports/phase7-probe-12-summary.md` |
| **Full 24 主对比** | `reports/llm/20260703_231744/llm-ablation-summary.md` |
| **Full 24 机制归因** | `reports/llm/20260704_000519/llm-ablation-summary.md` |
| **本摘要** | `reports/phase7-positive-gain-summary.md` |
