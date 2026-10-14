# Case Study: Memory Reuse（Holdout）

> 机制：`reposkill_agent/memory/matching.py`、`memory/retriever.py`、`eval/injection_policy.py`  
> 证据：Batch 5.4 memory 子集修复；Batch 5.10 memory_heavy **+12.5pp**

## 问题

Batch 5.3 6-task probe 上 `memory_heavy=0%`（L4/L5 均失败）。Holdout 任务（如 `inv_api_tax_holdout_01`）无法从 support 任务的成功 episodic/procedural memory 中受益；policy 大量 `mem_suppressed`，hint 质量或匹配逻辑有问题。

## 机制

### 1. Holdout ↔ support 配对

`seed_pair_task_id(holdout_task_id)` 将 `*_holdout_*` 映射到对应 support 任务（如 `inv_api_tax_holdout_01` → `inv_api_tax_01`）。Retriever 在 holdout 上优先拉取配对 support 的 procedural / episodic entries。

### 2. Domain + mechanism matching

`procedural_applies(procedural_tags, task)` 要求 procedural memory 的 domain tags（inventory/config/events/auth）与任务 domain 交集，或 mechanism tag 匹配。避免跨 repo 错误 hint。

### 3. Compact MemoryHint injection

MemoryHint v2 注入 compact 格式：repo convention（`REPO_CONVENTIONS`）、test signals（`extract_test_signals`）、procedural steps。`max_memory_hints` 按 category 限制（memory_primary 默认 3）。

### 4. Category policy

- `memory_heavy` → **`memory_primary`**：`allow_skills=False, allow_memory=True`
- `multi_file_api` / `repo_convention` → memory-only（Batch 5.8 移除 conservative_mix 后）
- Holdout 上 `exclude_episodic_failures=True`，避免失败 episode 污染

### 5. Test signal extraction

`extract_test_signals(test_output)` 从 pytest 输出提取可行动信号（如 "tests expect Result.ok — not int"），帮助 LLM 对齐 repo convention，尤其在 holdout 无 support trace 可见时。

## 效果

| 阶段 | memory_heavy | 说明 |
| --- | ---: | --- |
| 5.3 probe | 0% | holdout 完全失败 |
| 5.4 修复后 probe | **86%** | matching + policy 修复 |
| 5.10 medium48 | **84.4%** vs L2 71.9% | **+12.5pp** mean |

Batch 5.10 L5 mem_inj=157（2 repeats），mem_suppressed=230 — suppression 仍活跃，但注入的 hint 质量足够支撑 holdout 通过率提升。

## 典型场景：Result[T] convention

四个 medium repo 共享 **Result.ok / Result.err** 约定（见 `REPO_CONVENTIONS`）。Support 任务成功后写入 procedural memory；holdout 任务 retriever 匹配到 "return Result[T] not bare int/bool"，Developer 生成符合测试断言的 patch。

L2 无 memory，需在单次 run 中从 test failure 自行推断 convention — 在 holdout 边界条件下更容易失败。

## 局限

- Memory 依赖 support/holdout 配对设计；非配对任务收益有限
- `--seed-memory` 跨 repeat 持久化未纳入 Batch 5.10 主 eval
- context_heavy 任务 memory route 收益不明显（mean 持平）
- episodic memory 可能 stale；suppression 逻辑仍需保守

## 相关文档

- `reports/phase7-probe-12-summary.md` — 5.3 memory_heavy=0%
- `reports/phase7-variance-summary.md` — memory_heavy per-repeat 波动
- `docs/case-study-skill-gating.md` — skill 路径互补
