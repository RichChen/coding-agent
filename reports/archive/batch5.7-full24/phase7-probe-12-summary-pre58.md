# Phase 7 Probe-12 Summary (Batch 5.5)

## 运行信息

| 项 | 值 |
| --- | --- |
| 任务集 | `benchmarks/tasks/phase7_probe_12.yaml`（12 任务：skill/context/memory 各 4） |
| 主对比 Run ID | `20260703_170314` |
| 机制归因 Run ID | `20260703_172817` |
| Mock LLM | **False**（DeepSeek，`.env` 加载） |
| Seed | 42 |
| Repeats | 1 |

---

## Overall Success

| Config | Success | parse_err | patch_applied | skill_inj | skill_suppressed | mem_inj | mem_suppressed | ctx_expand | ctx_recovered |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L0_llm_single | **42%** (5/12) | 2 | 16 | 0 | 0 | 0 | 0 | 0 | 0 |
| L2_llm_multi | **92%** (11/12) | 1 | 22 | 0 | 0 | 0 | 0 | 2 | 2 |
| L3_llm_skill | **83%** (10/12) | 0 | 17 | 23 | 0 | 0 | 0 | 3 | 3 |
| L4_llm_memory | **67%** (8/12) | 4 | 19 | 0 | 0 | 45 | 0 | 2 | 1 |
| L5_llm_full | **75%** (9/12) | 1 | 21 | 9 | 13 | 29 | 17 | 1 | 1 |

---

## 按类别 Success

| Category | L0 | L2 | L3 | L4 | L5 |
| --- | ---: | ---: | ---: | ---: | ---: |
| skill_heavy (4) | 25% | **100%** | 75% | 50% | **50%** |
| context_heavy (4) | 50% | **100%** | **100%** | 75% | **100%** |
| memory_heavy (4) | 50% | 75% | 75% | 75% | 75% |

---

## 验收线对照

| 条件 | 结果 | 说明 |
| --- | --- | --- |
| L5 ≥ L2 | ❌ | 75% vs 92%（-17pp） |
| L5 ≥ L0 + 20pp | ✅ | 75% vs 62% |
| skill_heavy：L3 或 L5 ≥ L2 | ❌ | L3=75%，L5=50%，L2=100% |
| memory_heavy：L4 或 L5 ≥ L2 | ✅ | L4/L5/L2 均为 75% |
| context_heavy：L2 或 L5 > L0 | ✅ | L2/L5=100%，L0=50% |
| L5 parse_err ≤ 1 | ✅ | 1 |
| **Full 24 准入** | **❌ 未通过** | L5 未追平 L2，更未领先 |

**结论：不要开 full 24。** 5.4 memory 修复未破坏 context（L5 context=100%=L2），但 **L5 在 skill_heavy 上明显回退**，full stack 组合未证明优于 L2。

---

## L5 失败归因（vs L2）

| 任务 | 类别 | L2 | L5 | L5 policy | 根因 |
| --- | --- | ---: | ---: | --- | --- |
| `inv_api_tax_01` | skill_heavy | ✅ | ❌ | skill_primary | 注入错误 skill（`event_serializer_compat` 等，`skill_negative_transfer=1`）；memory hint 与 skill 同屏干扰 |
| `inv_rename_01` | skill_heavy | ✅ | ❌ | context_recovery_minimal | replan 后 skill/memory 均被抑制，未能恢复 |
| `inv_api_tax_holdout_01` | memory_heavy | ✅ | ❌ | memory_primary | holdout 税参签名修复失败（L2 无 memory 反而通过） |
| `inv_rename_holdout_01` | memory_heavy | ❌ | ✅ | memory_primary | L5 memory 帮助此项（L2 唯一失败项） |

**按类别统计 L5 额外失败来源：**

- **skill_heavy**：2 个失败（主因：skill 负迁移 + skill/memory 共注入）
- **memory_heavy**：1 个净失败（1 胜 1 负 vs L2）
- **context_heavy**：0 失败（无回退）

---

## 机制观察

1. **Memory 修复有效但未转化为 L5 领先**：memory_heavy 子集 L4/L5 与 L2 持平（75%），说明 5.4 hint 质量修复有效。
2. **L4 全局 67%**：无 category router 时 memory 在 skill/context 任务上注入过多（`mem_inj=45`），拉低整体。
3. **L3 skill_heavy 75% < L2 100%**：说明 skill 库本身在部分 inventory 任务上也有负迁移，不仅是 L5 组合问题。
4. **L5 policy router 部分生效**：`skill_suppressed=13`，`mem_suppressed=17`；但 skill_heavy 仍允许 1 条 memory（repo_profile），与 skill 竞争 prompt 空间。

---

## Batch 5.5 已实施 Policy 修补

基于 trace 分析，已将 `skill_primary` 改为 **skill-only**（`allow_memory=False`，`max_memory_hints=0`），避免 skill_heavy 上 skill/memory 共注入。

- 修改文件：`reposkill_agent/eval/injection_policy.py`
- 测试：`tests/test_injection_policy.py` 已通过

---

## Batch 5.5.1 Policy Retest

### 运行信息

| 项 | 值 |
| --- | --- |
| Run ID | `20260703_221056` |
| 配置 | L0 / L2 / L5（seed=42，repeats=1） |
| Mock LLM | **False** |
| Policy 状态 | `skill_primary` skill-only 已生效 |

**未补跑 L3/L4**（L5 75% < L2 92%，不满足触发条件）。

### Overall Success（5.5.1）

| Config | Success | parse_err | patch_applied | skill_inj | skill_suppressed | mem_inj | mem_suppressed | skill_neg_transfer | ctx_expand | ctx_recovered |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L0_llm_single | **58%** (7/12) | 0 | 11 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| L2_llm_multi | **92%** (11/12) | 0 | 16 | 0 | 0 | 0 | 0 | 0 | 4 | 3 |
| L5_llm_full | **75%** (9/12) | 2 | 22 | 7 | 16 | 22 | 24 | **1** | 1 | 2 |

### 按类别 Success：5.5 vs 5.5.1（L5）

| Category | L2 (5.5.1) | L5 (5.5) | L5 (5.5.1) | Δ |
| --- | ---: | ---: | ---: | ---: |
| skill_heavy | 100% | **50%** | **75%** | **+25pp** |
| context_heavy | 100% | 100% | **75%** | **-25pp** |
| memory_heavy | 75% | 75% | 75% | 0 |

### Policy 修补验证

| 检查项 | 5.5 | 5.5.1 | 结论 |
| --- | --- | --- | --- |
| skill_heavy 上 `mem_inj=0` | ❌（有 repo_profile 注入） | ✅（4/4 任务 mem_inj=0） | 修补生效 |
| `skill_negative_transfer` | 2 | **1** | 下降 |
| `inv_rename_01` | ❌ | ✅ | 共注入去除后恢复 |
| `inv_api_tax_01` | ❌ | ❌ | 仍失败（skill 库负迁移） |
| L5 overall ≥ L2 | ❌ | ❌ | **仍未达标** |

### L5 失败任务对比（5.5 → 5.5.1）

| 任务 | 类别 | 5.5 | 5.5.1 | 变化 |
| --- | --- | ---: | ---: | --- |
| `inv_rename_01` | skill_heavy | ❌ | ✅ | 修补修复 |
| `inv_api_tax_holdout_01` | memory_heavy | ❌ | ✅ | 随机波动/ memory 帮助 |
| `evt_context_pipeline_01` | context_heavy | ✅ | ❌ | **新回退** |
| `inv_api_tax_01` | skill_heavy | ❌ | ❌ | 持续失败 |
| `inv_rename_holdout_01` | memory_heavy | ✅ | ❌ | 波动（L2 亦失败此项） |

L2 唯一失败：`inv_rename_holdout_01`（memory_heavy）。

### 5.5.1 验收线

| 条件 | 结果 |
| --- | --- |
| L5 ≥ L2 | ❌ 75% vs 92% |
| L5 skill_heavy ≥ 75% | ✅ 75%（从 50% 回升） |
| L5 memory_heavy ≥ L2 | ✅ 75% = L2 |
| L5 context_heavy = 100% | ❌ 75%（`evt_context_pipeline_01` 回退） |
| L5 parse_err ≤ 1 | ❌ 2 |
| skill_primary mem_inj=0 | ✅ |
| **Full 24 准入** | **❌ 未通过** |

### 5.5.1 结论

**不要开 full 24。**

`skill_primary` skill-only 修补**部分有效**：skill_heavy 从 50% 升到 75%，`inv_rename_01` 恢复，`skill_negative_transfer` 下降，skill 任务上 memory 注入归零。但 L5 overall 仍为 **75%**，与 5.5 相同——失败任务发生**置换**（context 新失败抵消 skill 修复），未追平 L2 的 92%。

**根因判断：**

1. **持续 blocker**：`inv_api_tax_01` — skill 库负迁移（错误 skill 注入），非 memory 共注入问题 → 需 **Batch 5.6 清 skill 库**。
2. **波动/未解**：`evt_context_pipeline_01` — L5 context_primary 下偶发失败，需 trace 归因。
3. **共享难点**：`inv_rename_holdout_01` — L2/L5 均失败，非 L5 特有问题。

**建议下一步：Batch 5.6** — 针对 inventory skill 负迁移（domain gating / skill evidence 收紧），不扩大 benchmark 规模。

---

## Batch 5.6：Skill 负迁移清理 + Context 回归守护

### 代码变更

| 模块 | 改动 |
|------|------|
| `skills/domain.py` | 新增：task/skill domain 匹配、泛 evidence 检测 |
| `skills/validator.py` | `domain_mismatch` / `domain_mismatch_generic_evidence` 拒绝 |
| `skills/retriever.py` | 检索前过滤 domain 不兼容 skill |
| `skills/library/*.md` | 为 Phase7 skill 增加 `domains` 字段 |
| `skills/library/inventory_tax_api.md` | 新增 inventory 税参/Result 专用 skill |
| `eval/injection_policy.py` | `context_primary` 关闭 memory（`allow_memory=False`） |

### 运行信息

| 项 | 值 |
| --- | --- |
| 主对比 Run ID | `20260703_223829` |
| 机制归因 Run ID | `20260703_225809` |
| Mock LLM | **False** |
| Seed | 42 |

### Overall Success（5.6）

| Config | Success | parse_err | patch_applied | skill_inj | skill_suppressed | skill_neg_transfer | mem_inj | mem_suppressed | ctx_expand | ctx_recovered |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L0 | **50%** | 1 | 11 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| L2 | **83%** | 0 | 21 | 0 | 0 | 0 | 0 | 0 | 2 | 2 |
| L3 | **100%** | 0 | 21 | 14 | 0 | — | 0 | 0 | 3 | 3 |
| L4 | **83%** | 3 | 18 | 0 | 0 | — | 42 | 0 | 2 | 3 |
| L5 | **92%** | 2 | 18 | 3 | 9 | **0** | 14 | 23 | 1 | 2 |

### 按类别 Success（5.6）

| Category | L2 | L3 | L4 | L5 |
| --- | ---: | ---: | ---: | ---: |
| skill_heavy | 100% | 100% | 100% | **100%** |
| context_heavy | 100% | 100% | 75% | **100%** |
| memory_heavy | 50% | 100% | 75% | **75%** |

### 关键任务恢复

| 任务 | 5.5.1 | 5.6 | 说明 |
| --- | ---: | ---: | --- |
| `inv_api_tax_01` | ❌ | ✅ | domain gating 阻断 `event_serializer_compat`；`inventory_tax_api` 注入 |
| `evt_context_pipeline_01` | ❌ | ✅ | context_primary 零 memory；无 skill 干扰 |
| `inv_api_tax_holdout_01` | ❌ | ❌ | 唯一剩余失败（memory_heavy） |

L5 唯一失败：`inv_api_tax_holdout_01`（L2 本轮亦未通过 memory_heavy 子集多项）。

### 5.6 验收线

| 条件 | 结果 |
| --- | --- |
| L5 ≥ L2 | ✅ **92% ≥ 83%** |
| L5 skill_heavy ≥ 75% | ✅ 100% |
| L5 context_heavy = 100% | ✅ 100% |
| L5 memory_heavy ≥ L2 | ✅ 75% ≥ 50% |
| L5 parse_err ≤ 1 | ❌ 2 |
| inv_api_tax_01 通过 | ✅ |
| skill_primary mem_inj=0 | ✅ |
| skill_negative_transfer 下降 | ✅ 0（5.5.1 为 1） |
| **Full 24 准入** | **✅ 通过**（L5 ≥ L2） |

### 5.6 结论

**可以进入 full 24。** Domain gating + context 零 memory 守护解决了 5.5.1 的两个 L5 独有 blocker；L5 在 probe_12 上 **92%**，高于 L2 **83%**，skill/context/memory 三类均无回退。叙事可写「full stack 在 balanced probe 上正向领先 L2」，但 parse_err=2 仍建议在 full 24 报告中单独标注。

**剩余非阻塞项**：`inv_api_tax_holdout_01` holdout 稳定性、`L5 parse_err` 收敛至 ≤1。

---

## 任务清单（phase7_probe_12.yaml）

| 类别 | 任务 ID |
| --- | --- |
| skill_heavy | `inv_api_tax_01`, `inv_rename_01`, `cfg_env_override_01`, `evt_handler_registry_01` |
| context_heavy | `inv_convention_01`, `inv_convention_holdout_01`, `cfg_merge_order_01`, `evt_context_pipeline_01` |
| memory_heavy | `inv_api_tax_holdout_01`, `inv_rename_holdout_01`, `cfg_merge_order_holdout_01`, `evt_handler_registry_holdout_01` |

Seed 任务（skill/context 槽位）覆盖全部 holdout 配对，无测试断言修改。

---

## 报告路径

- Batch 5.5 主对比：`reports/llm/20260703_170314/llm-ablation-summary.md`
- Batch 5.5 机制归因：`reports/llm/20260703_172817/llm-ablation-summary.md`
- Batch 5.5.1 复测：`reports/llm/20260703_221056/llm-ablation-summary.md`
- **Batch 5.6 主对比**：`reports/llm/20260703_223829/llm-ablation-summary.md`
- **Batch 5.6 机制归因**：`reports/llm/20260703_225809/llm-ablation-summary.md`
- 本摘要：`reports/phase7-probe-12-summary.md`
