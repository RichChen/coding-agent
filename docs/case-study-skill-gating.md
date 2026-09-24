# Case Study: Skill Domain Gating

> 机制：`reposkill_agent/skills/domain.py`、`skills/validator.py`、`eval/injection_policy.py`  
> 证据：Probe-12 Batch 5.5→5.6；Full 48 Batch 5.10 skill_heavy **+15.0pp**

## 问题

Batch 5.5 probe-12 上 L5=75% **低于** L2=92%。失败归因显示 `skill_heavy` 任务注入了**错误 domain** 的 SkillCard（如 inventory 任务注入 `event_serializer_compat`），触发 `skill_negative_transfer`，memory hint 与 skill 同屏进一步干扰 patch 生成。

L2 无 augmentation，反而在 skill 任务上更稳。

## 机制

### 1. Domain compatibility gate

`domain_compatible(skill, task)` 检查 SkillCard 的 domain tags（`inventory` / `config` / `events` / `auth`）与任务 tags 是否匹配。仅含 generic evidence 的 skill 在 domain 不匹配时被拒（`domain_mismatch_generic_evidence`）。

### 2. Evidence gating

`SkillValidator` 要求 skill 的 `evidence_requirements` 在运行时 context 中可验证（issue text、tags、test_output、expected_files 等）。Phase 7 扩展了 `EVIDENCE_TAG_ALIASES`，使 `skill_heavy`、`multi_file_api` 等 mechanism tag 可 satisfy evidence token。

### 3. Category policy router

`skill_heavy` 任务走 **`skill_primary`** route：`allow_skills=True, allow_memory=False, max_skills=1`。避免 skill 与 memory 同屏注入（Batch 5.5 的主干扰源）。

`context_heavy` / `traceback_repair` 走 **`context_primary`** / minimal route：零 augmentation，依赖 context expansion 而非 skill/memory。

## 效果

| 阶段 | skill_heavy L5 | skill_neg | 说明 |
| --- | ---: | ---: | --- |
| 5.5 probe | 50% | 1 | 错误 skill 注入 |
| 5.6 probe | 75%→92% overall | 0 | domain gating + skill-only |
| 5.10 medium48 | **80%** vs L2 65% | 1 | **+15pp** mean |

Batch 5.10 上 L5 skill_inj=13（2 repeats aggregate），skill_suppressed=509 — 大量候选被 gate 掉，仅注入高置信 skill。

## 典型 trace 模式

1. Retriever 返回 5–10 个 SkillCard 候选
2. Validator 拒绝 domain mismatch / missing evidence / negative_transfer
3. Policy router 在 skill_heavy 上仅注入 0–1 个 skill
4. Developer prompt 保持 compact，parse_err 可控

## 局限

- `multi_file_api` 仍共享难点；gating 降低负迁移但不能保证跨文件推理
- 小样本 category（4 tasks labeled multi_file_api in aggregate）方差大
- 依赖手工 SkillCard 质量与 evidence token 设计

## 相关文档

- `reports/phase7-probe-12-summary.md` — 5.5 失败归因
- `reports/phase7-full24-failure-analysis.md` — conservative_mix 干扰
- `docs/case-study-memory-reuse.md` — memory 路径互补
