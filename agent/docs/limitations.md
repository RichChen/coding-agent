# Limitations

> Phase 7.1 实验收口后的诚实披露清单。主结论仍成立，但适用范围有界。

## Benchmark & Generalization

### Synthetic medium repos，不是 SWE-bench

- 48 任务分布在 4 个 **手工构造** 的 Python medium repo（inventory、config_loader、event_pipeline、auth_rules）
- 任务含 skill/memory/context 标签与 holdout 配对，**针对本系统机制设计**
- 未在 SWE-bench、HumanEval、真实 GitHub issue 上验证
- **不能** 声称对工业级 code repair 的泛化能力

### 旧 eval 不是主结论

- `phase6_tiny_24`：plumbing，A0–A5 全 1.00 饱和
- `phase6_hard_12`：早期 real LLM 上 L2≈92%，L3/L4/L5 < L2
- 这些结果驱动了 Phase 7 改造，但 **不应** 与 Batch 5.10 主结论混用

## Statistical Rigor

### repeats=2，不是大规模统计显著性

- Batch 5.10 仅 2 次 independent repeat（seed=42）
- 报告 mean ± std，**未** 做 bootstrap / t-test / 置信区间
- +9.4pp mean delta 在 n=2 下不能声称 statistical significance
- **不建议** 再跑 repeats=3 追显著性 — 成本高，边际收益低

### L5 run-to-run 方差高于 L2

| Config | Std |
| --- | ---: |
| L2 | ±2.1pp |
| L5 | ±5.2pp |

- Repeat 0: L5=75.0% vs L2=72.9%（+2.1pp）
- Repeat 1: L5=85.4% vs L2=68.8%（+16.7pp）
- Full system 引入 skill/memory/policy 后波动更大；方向稳定（两次均 L5≥L2）但 margin 不稳定

## Category-Level Gaps

### Primary category vs multi-label tags

- 任务 YAML 使用多标签（如 `[multi_file_api, skill_heavy, inventory]`）
- Ablation 报告的 `By Task Category` 使用 `task_category()` 取**单一主类别**（优先级：skill_heavy > memory_heavy > context_heavy > multi_file_api > traceback_repair > repo_convention）
- Overall success 不受影响；category 表是非重叠分桶，**不是** multi-label 频次统计
- 例：8 题带 `multi_file_api` 标签，但 primary bucket 仅 4 题（其余被 skill_heavy/memory_heavy 优先归入）

### context_heavy / traceback_repair 非主要增益来源

- context_heavy：L5 mean = L2 mean = 85.0%（2-repeat）
- traceback_repair：L5 mean = L2 mean = 70.0%（仅 5 tasks）
- Context expansion 是 L2 baseline 能力；L5 augmentation 未在此两类上带来额外 delta
- Repeat 0 context_heavy 曾 L5 < L2（−10pp）

### multi_file_api 仍为共享难点

- L5 mean 50% vs L2 37.5%（+12.5pp mean，但绝对率仍低）
- 跨文件 API 修改需要更强 reasoning；机制 gating 降低负迁移但不解决根本难度
- Batch 5.9 单次上 multi_file_api L5=25% < L2=50%，mean 被 Repeat 1 拉高

## Mechanism & Engineering

### Domain gating audit（Batch 6.0-audit-fix）

- Batch 5.10 跑时，`skills/domain.py` 的 `TASK_DOMAIN_TAGS` 缺少 `auth`（memory 侧已有），auth 任务在 skill 层 domain 不设防
- 审计结论：6/48 auth 题，L5 子集表现不劣于 L2；**不推翻** +9.4pp 主结论
- 已修复：`auth` 加入 `TASK_DOMAIN_TAGS`；memory 改为引用同一常量
- 表述应使用：「domain/evidence gating 抑制跨域 skill 注入」，而非「fully covers all domains without gaps」

### Context expansion：tests/ 只读

- Context expansion 可将 `tests/` 加入可读上下文
- Batch 5.10 无证据显示 tests 被写入；但代码层曾允许 expanded test paths 进入 writable scope
- 已修复：`LLMDeveloperAgent` 分离 readable vs writable paths，**禁止 patch tests/**

### Online memory setting

- Memory-enabled configs（L4/L5）在**同一 repeat 内**累积 episodic/procedural/repo profile
- Repeat 间 memory 目录隔离；Batch 5.10 未使用 `--seed-memory`
- L5/L4 收益部分来自在线经验积累——这是 memory 机制设计，应在报告中披露
- Tag-filtered memory probe 可能包含不计入 success 分母的 warmup 任务（full48 主 eval 不受影响）

### SkillCard / MemoryHint 依赖手工 curation

- Skill library 与 memory conventions 针对 benchmark repo 设计
- 新 repo 需要重新编写 SkillCard、repo profile、procedural templates
- 未验证 zero-shot 迁移到新 codebase

### Parse error 未消除

- L5 total parse_err = 10（2 repeats），与 L2 相同
- JSON repair retry 有效但未归零；prompt 膨胀与 augmentation 仍增加 parse 风险
- skill_negative_transfer = 1（≤5 验收线，但非零）

### External baselines 未实跑

- `reposkill_agent/baselines/` 与 `run_external_baselines.py` 已实现，标记 **optional/skip**
- 未与 OpenHands agent、SWE-agent、Aider 等同 backend 对比
- 内部 L0/L2/L5 ablation 是唯一定量 baseline

## Cost & Reproducibility

### 真实 LLM eval 成本高

- Batch 5.10 full 48 × 3 configs × 2 repeats ≈ 3.2 小时 + API 费用
- 结果依赖 DeepSeek model version、API 稳定性
- 未固定 model snapshot ID；复现可能有 run-to-run 差异

### `--seed-memory` 未纳入主 eval

- 跨 repeat 持久化 memory 目录的 seeded memory 模式在 deterministic eval 有效
- Batch 5.10 主 eval 未使用 `--seed-memory`；holdout 收益来自单 run 内 retriever
- Batch 5.10 结果在 auth-domain 同步修复前生成；审计表明无 material effect on overall delta

## What We Can Still Claim

在以上限制内，以下表述有证据支撑：

1. RepoSkillAgent 是 **真实 LLM agent 能力增强系统**（非 eval framework demo）
2. 48 medium tasks、2 real DeepSeek repeats：L5 **80.2% ± 5.2pp** vs L2 **70.8% ± 2.1pp**
3. 两次 repeat 均 L5 ≥ L2；parse_err 不高于 L2
4. 收益集中在 skill-heavy、memory-heavy、repo_convention
5. 机制迭代有完整 development history（probe → 24 → 48 → variance）
6. Domain/evidence gating 用于抑制跨域 skill 注入；auth-domain 同步缺口已在 audit 中发现并修复

## 相关文档

- `reports/phase7-variance-summary.md` — 方差明细
- `docs/current-evidence.md` — 证据分层
- `reports/phase7-positive-gain-summary.md` — 最终叙事
