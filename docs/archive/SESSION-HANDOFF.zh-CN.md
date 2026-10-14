# 会话交接文档（Codex → Cursor / 新 Codex 会话）

> **最后更新**：2026-07-04（Batch 6 收口）  
> **用途**：Codex 主会话因上下文过长无法 resume 时，用本文档恢复项目目标、共识、进度与下一步。  
> **项目路径**：`D:\crq\src\coding-agent`

---

## 1. 一句话定位

**RepoSkillAgent**：面向字节类 Agent 研发实习的 **真实 LLM Coding Agent 能力增强项目**——通过 **PlanAct + Multi-Agent + Skill + Memory**，让 DeepSeek 在 medium repo 修复任务上比 vanilla multi-agent baseline 更可靠；**评测是证据链，不是项目主角**。

与旧项目 `coding-harness` 的分工：

| 项目 | 叙事 |
| --- | --- |
| `coding-harness` | Harness / eval / trace / policy 强——证明「可测、可控、可回放」 |
| `coding-agent`（本项目） | Agent 能力机制强——证明「Planner / 分工 / Skill / Memory 带来真实 LLM 正向收益」 |

---

## 2. 最终主结果（Batch 5.10 · 权威）

**Run `20260704_092308`** · `phase7_medium_48` · 48 tasks · 4 repos · seed=42 · **repeats=2** · Mock=False · ~3.2h

| Config | Mean | Std | Repeat 0 | Repeat 1 |
| --- | ---: | ---: | ---: | ---: |
| L0 | 45.8% | ±2.1pp | 47.9% | 43.8% |
| L2 | 70.8% | ±2.1pp | 72.9% | 68.8% |
| **L5** | **80.2%** | **±5.2pp** | 75.0% | 85.4% |

- **L5 − L2 = +9.4pp** · 两次 repeat 均 L5 ≥ L2
- parse_err：L5=10，L2=10（不高于 L2）
- skill_heavy +15pp · memory_heavy +12.5pp · multi_file_api +12.5pp

**实验收口。** 不再跑 repeats=3 或继续调 benchmark 追分。

报告：`reports/phase7-variance-summary.md` · 叙事：`reports/phase7-positive-gain-summary.md`

---

## 3. 已达成共识的决策（勿推翻）

1. **不推倒重来** — OpenHands SDK / SWE-agent / Aider 仅作 optional external baseline
2. **真实 LLM 正向收益已达成** — L5 mean > L2 mean，两次 repeat 均 L5≥L2
3. **主证据 = Batch 5.10** — mean±std 表述；5.9 单次作 supporting；24/probe 作 development history
4. **安全** — DeepSeek 配置在 `.env`；严禁 API key 写入代码/文档/报告
5. **诚实 limitations** — 见 `docs/limitations.md`

---

## 4. 阶段进度

### Phase 0–6 ✅

Planner、Multi-Agent、Skill、Memory MVP、deterministic A/B、LLM 接入、L0–L5 ablation。

### Phase 7.1 ✅（实验完成）

| Batch | 内容 | 状态 |
| --- | --- | --- |
| 1 | evidence + external baselines scaffold | ✅ |
| 2 | 3 medium repos + phase7_medium_24 | ✅ |
| 3 | SkillCard v2 + MemoryHint v2 + gating | ✅ |
| 4 | context expansion + JSON repair | ✅ |
| 4.5 | mechanism smoke | ✅ |
| 5.4 | memory 子集修复（0%→86%） | ✅ |
| 5.5–5.6 | probe-12 + domain gating | ✅ |
| 5.7–5.8 | full 24 + 干扰路由修复 | ✅ |
| 5.9 | medium 48 扩展（单次 +10.4pp） | ✅ |
| **5.10** | **variance check repeats=2（+9.4pp mean）** | ✅ |
| **6** | **README / docs / case studies / limitations** | ✅ |

---

## 5. 技术架构快照

```
WorkspaceAdapter (FakeAdapter 用于单测/CI)
    └── TaskGraphPlanner (PlanAct)
            └── Role Agents + LLMDeveloperAgent (DeepSeek)
            └── SkillCard v2 + domain/evidence gating
            └── MemoryHint v2 (episodic/procedural/repo profile)
            └── Augmentation policy router (injection_policy.py)
            └── Context expansion + JSON repair retry
```

**Benchmark 分层**：

1. `phase6_tiny_24` — plumbing（非主结论）
2. `phase6_hard_12` — deterministic / 早期 real LLM（开发历史）
3. **`phase7_medium_48`** — **最终主战场**（48 tasks × 4 repos）

---

## 6. 关键文档索引

| 文件 | 用途 |
| --- | --- |
| **`docs/project-chronology.zh-CN.md`** | **全历程：每次改动、原因、结果** |
| **`docs/code-reading-guide.zh-CN.md`** | **代码阅读顺序 + 带问题清单模板** |
| `README.md` | 项目首页 + Batch 5.10 主结果 |
| `reports/phase7-variance-summary.md` | **权威方差报告** |
| `reports/phase7-positive-gain-summary.md` | 最终叙事摘要 |
| `docs/current-evidence.md` | 证据分层（Phase 6 + Phase 7） |
| `docs/limitations.md` | 诚实限制 |
| `docs/case-study-*.md` | 3 个机制 case study |
| `PHASE7_1-POSITIVE-GAIN-HARDENING-PLAN.zh-CN.md` | Phase 7.1 执行主文档 |
| `benchmarks/tasks/phase7_medium_48.yaml` | 48 任务定义 |

---

## 7. 工程自检

```powershell
cd D:\crq\src\coding-agent
conda activate coding-agent
pytest
ruff check .
python scripts/run_mechanism_smoke.py
```

---

## 8. 新会话首条消息模板

### 给 Codex（规划 / 决策）

```text
请先读 docs/SESSION-HANDOFF.zh-CN.md 和 reports/phase7-variance-summary.md。
Batch 5.10 已完成：L5=80.2%±5.2pp vs L2=70.8%±2.1pp，实验收口。
Batch 6 文档已完成。如需后续工作，建议：external baseline 实跑、SWE-bench 迁移、或 OpenHands adapter 深化。
```

### 给 Cursor Composer（实现）

```text
Phase 7.1 实验已收口。主证据在 reports/phase7-variance-summary.md。
不要改 benchmark 或再跑真实 LLM eval，除非用户明确要求新 phase。
```

---

## 9. 变更记录

| 日期 | 说明 |
| --- | --- |
| 2026-07-03 | 初版：Batch 1–5.3 进度 |
| 2026-07-04 | Batch 5.10 完成 + Batch 6 文档收口；实验结束 |
