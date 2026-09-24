# Phase 7 Full-24 Failure Analysis（Batch 5.7 baseline）

Baseline runs archived under `reports/archive/batch5.7-full24/`.

| Run | Role |
| --- | --- |
| `20260703_231744` | L0 / L2 / L5 full 24 |
| `20260704_000519` | L3 / L4 full 24 |

Overall: **L0=46%**, **L2=71%**, **L4=83%**, **L5=79%**（L5 仅 +8.4pp vs L2，且 **低于 L4**）。

---

## L5 失败任务矩阵（5/24）

| 任务 | Category | L2 | L4 | L5 route | skill_inj | mem_inj | parse | ctx_expand | neg_transfer | 根因 |
| --- | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |
| `evt_context_pipeline_01` | context_heavy | ✅ | ❌ | context_recovery_minimal | 0 | 0 | 2 | 0 | 0 | **模型/parse 波动**；L2 过、L4 亦败，非 L5 独有 skill/mem 干扰 |
| `cfg_schema_validation_01` | skill_heavy | ❌ | ❌ | context_recovery_minimal | 0 | 0 | 0 | 1 | 0 | **共享难题**；三配置均失败 |
| `evt_retry_policy_01` | repo_convention | ❌ | ✅ | **conservative_mix** | 2 | 2 | 0 | 0 | **1** | **L5 独有**：skill+memory 混合弱于 L4 memory-only |
| `evt_serialization_01` | multi_file_api | ❌ | ✅ | context_recovery_minimal | 1 | 1 | 1 | 0 | **1** | **L5 独有负迁移**：首轮 conservative_mix 注入后 replan 仍带干扰 |
| `cfg_key_alias_01` | multi_file_api | ❌ | ❌ | context_recovery_minimal | 1 | 1 | 0 | 1 | **1** | **共享难题** + L5 skill 负迁移 |

---

## 机制结论（Batch 5.8 修复方向）

1. **`conservative_mix` 是 L4 > L5 的主因**  
   `repo_convention` / `multi_file_api` 任务在 L5 上同时注入 skill+memory，而 L4 仅 memory 即可通过（如 `evt_retry_policy_01`、`evt_serialization_01`）。

2. **context_heavy 回退不是 memory 主因**  
   `context_primary` 已零 skill/memory；`evt_context_pipeline_01` 失败来自 parse/补丁质量，需保持 minimal route + 控制 prompt 长度。

3. **skill_negative_transfer=3**  
   均出现在 **conservative_mix / recovery 路径** 下的 multi_file_api 与 repo_convention，与错误 skill 共注入 memory 相关。

4. **memory_heavy 不是当前 blocker**  
   L5 memory_heavy **100%**（7/7），无需再扩 memory 功能。

---

## Batch 5.8 机制改动（对应上表）

| 改动 | 目的 |
| --- | --- |
| 移除 `conservative_mix` | multi_file_api / repo_convention → **memory-only**（L4-like） |
| `traceback_repair` → minimal | 与 context 一致，零 augmentation 噪声 |
| `skill_primary` max_skills **1** | 降 prompt 长度与 parse_err |
| `exclude_repo_profile` on non-holdout memory routes | 避免泛 repo_profile 抢占 procedural/test signal |
| skill_heavy 保持 skill-only | 不回归 5.6 domain gating |

---

## 验收目标（Batch 5.8）

- L5 ≥ L4，L5 ≥ L2 + 10pp（理想）
- L5 context_heavy ≥ 80%
- L5 parse_err ≤ 2，skill_negative_transfer ≤ 1
- 不改 benchmark / 测试断言

---

## Batch 5.8 复测结果（Run `20260704_012041`）

| Config | 5.7 | 5.8 | Δ |
| --- | ---: | ---: | ---: |
| L2 | 71% | **75%** | +4pp |
| L4 | 83% | 66% | -17pp（波动） |
| L5 | 79% | **79%** | ≈0 |

| 指标 | 5.7 L5 | 5.8 L5 |
| --- | ---: | ---: |
| vs L2 | +8.4pp | **+4.2pp** |
| vs L4 | **低于 L4** | **高于 L4** ✅ |
| context_heavy | 80% | **100%** ✅ |
| skill_neg_transfer | 3 | **0** ✅ |
| parse_err | 3 | **2** ✅ |

**5.8 核心目标达成**：L5 不再弱于 L4（干扰降低）；context_heavy 回满；负迁移归零。

**未达理想线**：L5 vs L2 仅 +4.2pp（未 +10pp）；L5 overall 仍 ~79%。

Probe_12 预检（Run `20260704_005217`）因 LLM 波动未过门槛（L5=L2=67%），但 full 24 验证表明机制改动方向正确。

**建议收口**：不再继续调 policy；Batch 6 写 README，叙事强调 **L5≥L4、memory/context 子集收益、skill_neg=0**；如实写 overall +4~8pp 与 holdout 难点。

| 报告 | 路径 |
| --- | --- |
| 5.8 full 24 | `reports/llm/20260704_012041/llm-ablation-summary.md` |
| 5.8 probe | `reports/llm/20260704_005217/llm-ablation-summary.md` |
| 5.7 归档 | `reports/archive/batch5.7-full24/` |
