# Phase 7 Variance Summary（Batch 5.10）

**目标：** 对 `phase7_medium_48` 的 L0/L2/L5 做 repeats=2 真实 DeepSeek 方差估计，不改代码、不改 benchmark。

| 项 | 值 |
| --- | --- |
| Task file | `benchmarks/tasks/phase7_medium_48.yaml` |
| Run ID | `20260704_092308` |
| Configs | L0_llm_single, L2_llm_multi, L5_llm_full |
| Repeats | 2 |
| Seed | 42 |
| Mock LLM | False |
| 耗时 | ~3.2 h |

---

## Overall Success（mean ± std）

| Config | Mean | Std | Repeat 0 | Repeat 1 | parse_err（合计） |
| --- | ---: | ---: | ---: | ---: | ---: |
| L0 | **45.8%** | ±2.1pp | 47.9% (23/48) | 43.8% (21/48) | 3 |
| L2 | **70.8%** | ±2.1pp | 72.9% (35/48) | 68.8% (33/48) | 10 |
| L5 | **80.2%** | ±5.2pp | 75.0% (36/48) | 85.4% (41/48) | 10 |

**L5 − L2 mean delta: +9.4pp**（Repeat 0: +2.1pp；Repeat 1: +16.7pp）

两次 repeat 均满足 **L5 ≥ L2**（75.0% ≥ 72.9%；85.4% ≥ 68.8%）。

---

## vs Batch 5.9（repeats=1 单次参考）

| Config | 5.9 单次 | 5.10 mean | Δ |
| --- | ---: | ---: | ---: |
| L0 | 47.9% | 45.8% | −2.1pp |
| L2 | 68.8% | 70.8% | +2.0pp |
| L5 | 79.2% | 80.2% | +1.0pp |
| **L5−L2** | **+10.4pp** | **+9.4pp** | −1.0pp |

单次结果落在 mean±std 范围内；**+10pp 量级正向收益在 repeats=2 下仍成立**。

---

## parse_err

| Config | Repeat 0 | Repeat 1 | Mean / repeat | Total |
| --- | ---: | ---: | ---: | ---: |
| L0 | 2 | 1 | 1.5 | 3 |
| L2 | 3 | 7 | 5.0 | 10 |
| L5 | 6 | 4 | 5.0 | 10 |

- L5 total parse_err **不高于** L2（均为 10）
- L5 skill_negative_transfer：1（与 5.9 一致，≤5 线）

---

## Category-level L5 vs L2（2-repeat mean）

| Category | Tasks | L2 mean | L5 mean | Δ (L5−L2) | L5≥L2 |
| --- | ---: | ---: | ---: | ---: | --- |
| skill_heavy | 10 | 65.0% | 80.0% | **+15.0pp** | ✅ |
| memory_heavy | 16 | 71.9% | 84.4% | **+12.5pp** | ✅ |
| multi_file_api | 4 | 37.5% | 50.0% | **+12.5pp** | ✅ |
| repo_convention | 3 | 83.3% | 100% | **+16.7pp** | ✅ |
| context_heavy | 10 | 85.0% | 85.0% | 0.0pp | ≈ |
| traceback_repair | 5 | 70.0% | 70.0% | 0.0pp | ≈ |

### 各 repeat 的 category 波动（L5 vs L2）

| Category | R0 Δ | R1 Δ | 备注 |
| --- | ---: | ---: | --- |
| skill_heavy | +10pp | +20pp | 两次均正向 |
| memory_heavy | +6pp | +19pp | 两次均正向 |
| context_heavy | **−10pp** | +10pp | R0 略回退，R1 拉回 |
| multi_file_api | 0pp | +25pp | R0 持平，R1 明显增益 |
| repo_convention | 0pp | +33pp | R0 已满分 |
| traceback_repair | 0pp | 0pp | 小样本，无差异 |

**解读：** memory/skill 子集在两次 run 中均 L5 > L2；context_heavy 在 repeat 0 出现单次 −10pp，但 2-repeat mean 持平；L5 的 overall std（±5.2pp）高于 L2（±2.1pp），主要来自 repeat 0/1 之间 75% vs 85% 的摆动，需在 README 中诚实披露。

---

## 验收判断（Batch 5.10 标准）

| 条件 | 结果 |
| --- | --- |
| L5 mean > L2 mean | ✅ 80.2% > 70.8% |
| L5−L2 mean ≥ +8pp | ✅ +9.4pp |
| 两次 repeat 均 L5 ≥ L2 | ✅ |
| L5 parse_err 不高于 L2 | ✅ 10 vs 10 |
| L5 mean > L0 + 20pp | ✅ +34.4pp |

**结论：强通过。** 支持 README 使用 **mean ± std** 表述；**不建议** 再跑 repeats=3（L5 std 已可见，成本/收益比偏低）。

---

## 建议 README 表述

> On **48 medium repo tasks** (4 repos, seed=42), we report **2 independent repeats** with real DeepSeek. **L5 (PlanAct + MultiAgent + Skill + Memory) achieves 80.2% ± 5.2pp vs 70.8% ± 2.1pp for L2** (+9.4pp mean; both repeats L5 ≥ L2). Category gains concentrate in **memory-heavy (+12.5pp)** and **skill-heavy (+15.0pp)**; context-heavy is flat on mean with run-to-run variance. Parse errors are not elevated vs L2 (10 total each).

**不推荐：** “单次 +10.4pp” 作为唯一主结论 — 应改为 mean±std + 两次 repeat 明细。

**不推荐：** repeats=3 — 除非有审稿硬性要求；当前 repeats=2 已足够支撑“方向稳定、方差可解释”的叙事。

---

## 报告路径

| 文档 | 路径 |
| --- | --- |
| 原始 ablation JSON | `reports/llm/20260704_092308/llm-ablation-summary.json` |
| 原始 ablation MD | `reports/llm/20260704_092308/llm-ablation-summary.md` |
| 5.9 单次 48 题 | `reports/phase7-medium48-summary.md` |
| **本摘要** | `reports/phase7-variance-summary.md` |
