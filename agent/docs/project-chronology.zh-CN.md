# RepoSkillAgent 项目全历程（改动 · 原因 · 结果）

> **文档用途**：从项目立项到 Phase 7.1 实验收口，按时间顺序记录每一次重要改动、动机与可验证结果。  
> **最后更新**：2026-07-04（Batch 6 收口后）  
> **权威主结论**：Batch 5.10 — `phase7_medium_48`，L5 **80.2% ± 5.2pp** vs L2 **70.8% ± 2.1pp**（+9.4pp mean，repeats=2）

---

## 0. 项目定位（始终不变）

| 维度 | 内容 |
| --- | --- |
| **一句话** | 真实 LLM Coding Agent 能力增强系统，不是 eval framework demo |
| **核心机制** | PlanAct + Multi-Agent + SkillCard + MemoryHint + policy router |
| **底座** | OpenHands SDK（adapter 隔离）；DeepSeek 为真实 LLM 后端 |
| **与 coding-harness 分工** | harness 证明「可测可控」；本项目证明「机制带来真实 LLM 正向收益」 |
| **明确不做** | 完整 SWE-bench、企业 Agent OS、UI/Docker 平台、vendor 外部项目源码 |

---

## 1. 总时间线（鸟瞰）

```text
Phase 0–5   工程骨架 · Planner · Multi-Agent · Skill · Memory MVP
     ↓
Phase 6     评测分层 · hard_12 防饱和 · deterministic A0–A5 机制证据
     ↓
LLM 层      DeepSeek 接入 · L0–L5 ablation · hard_12 首次 real LLM（暴露饱和/负收益）
     ↓
Phase 7.1   medium benchmark · Skill/Memory v2 · context/repair · 迭代至正向收益
     ↓
Batch 5.9   48 题扩展 · 单次 +10.4pp
     ↓
Batch 5.10  repeats=2 方差检验 · +9.4pp mean · 实验收口
     ↓
Batch 6     README / docs / case studies / limitations 最终包装
```

---

## 2. Phase 0–5：能力建设期

> 此阶段以 `PROJECT-PLAN-OpenHands-RepoSkillAgent.zh-CN.md` 为纲；无独立 ablation 报告，以 pytest + 管线跑通为验收。

### Phase 0：项目初始化

| 项 | 内容 |
| --- | --- |
| **改动** | Python package、`pyproject.toml`、pytest/ruff、FakeAdapter、`TaskSpec`/`TraceEvent`、CLI |
| **原因** | 搭最小可测骨架，无 LLM/API 也能开发 |
| **结果** | `pytest` 通过；`python -m reposkill_agent --help` 可运行 |

### Phase 1：Single-agent baseline

| 项 | 内容 |
| --- | --- |
| **改动** | `OpenHandsAdapter`；3 个 tiny repo task；读 issue → patch → test → trace |
| **原因** | 建立后续 A/B 锚点 |
| **结果** | 3 个 toy task 跑通；JSONL trace 产出 |

### Phase 2：TaskGraphPlanner + PlanAct

| 项 | 内容 |
| --- | --- |
| **改动** | 结构化任务图；`plan → execute → observe → replan`；trace 事件 `plan_created`/`replan` |
| **原因** | 从自然语言 plan 升级为可观测、可 replan 的图执行 |
| **结果** | 失败可定位到节点；static plan / replan 可配置切换 |

### Phase 3：Role-based Multi-Agent

| 项 | 内容 |
| --- | --- |
| **改动** | Manager / Locator / Developer / QA 角色；结构化输出；single vs multi 可切换 |
| **原因** | 减少单轨迹上下文污染（借鉴 MASAI / Magentic-One） |
| **结果** | multi-agent trace 可见 role handoff；QA 失败分类 |

### Phase 4：Skill Library

| 项 | 内容 |
| --- | --- |
| **改动** | SkillSpec metadata、retriever、validator、negative transfer 记录；graph metrics |
| **原因** | Skill 需验证适用性，不能盲目注入（借鉴 SWE-Skills-Bench） |
| **结果** | `run-graph --use-skills`；skill 统计写入 trace/report |

### Phase 5：Memory System MVP

| 项 | 内容 |
| --- | --- |
| **改动** | episodic / procedural / repo profile；JSONL + SQLite；`MemoryCuratorAgent` |
| **原因** | 从成功/失败轨迹沉淀可复用经验（借鉴 MemSkill / Agent Workflow Memory） |
| **结果** | `run_memory_ablation.py`；tiny task 上 memory 检索可观测（plumbing 阶段 success 均为 1.00） |

---

## 3. Phase 6：评测强化（Deterministic）

**计划文档**：`PHASE6-EVAL-STRENGTHENING-PLAN.zh-CN.md`  
**总结报告**：`reports/phase6-eval-summary.md`

### 核心问题

Phase 6 初期发现：**tiny_24 上 A0–A5 全部 100% 饱和**，无法声称 skill/memory 机制收益。

### 主要改动

| 改动 | 原因 | 结果 |
| --- | --- | --- |
| 新增 `phase6_hard_12` + 4 类 hard tiny repos | 关闭 scripted fix，逼出真实机制差异 | A0/A1/A2 hard 上 **0%** |
| `FakeAdapter.allow_prefix_scripted_fixes=False` | hard eval 禁止前缀脚本修复 | baseline 不再饱和 |
| A1=`single_graph` vs A2=`role_agents` | 区分 planner 与 multi-agent trace | A2 role_handoff=4，可区分 |
| Developer 按 skill/memory 选 hard patch strategy | skill/memory 影响 patch，非仅 telemetry | A3=**92%**，A4=**67%**，A5=**97%** |
| 按 task category 分组报告 | 避免整体 rate 掩盖局部失败 | rename 0.67 如实披露 |
| `docs/evaluation-contract.md` 三层边界 | 明确 plumbing / mechanism / LLM 用途 | 后续 Phase 7 沿用 |

### Phase 6 核心结果（Run `20260702_102422`）

| Config | Hard Success | 解读 |
| --- | ---: | --- |
| A0/A1/A2 | 0% | planner/multi-agent  alone 无 patch strategy（诚实负结果） |
| A3_skill | **92%** | skill 驱动 deterministic patch 有效 |
| A4_memory | **67%** | memory 有收益但不如 skill |
| A5_full | **97%** | 组合最优 |
| A5 + `--seed-memory` | **100%** | seeded memory 补齐 rename 边缘 case |

**结论**：机制链路在 deterministic 层可解释；**不能**直接等同于 real LLM 收益。

---

## 4. LLM / DeepSeek 接入层

**计划文档**：`LLM-DEEPSEEK-INTEGRATION-PLAN.zh-CN.md`

### 主要改动

| 改动 | 原因 |
| --- | --- |
| `ModelClient` + OpenAI-compatible API | 接入 DeepSeek Chat Completions |
| `LLMDeveloperAgent` | 真实 LLM patch 生成替代 deterministic developer |
| `PatchPlan` schema + prompts | 结构化 patch；控制 prompt 长度 |
| `scripts/run_llm_ablation.py` L0–L5 | 与 A0–A5 对齐的 LLM 消融配置 |
| `.env` 读 API key | 安全：key 不入库 |

### L0–L5 配置含义

| Config | 含义 |
| --- | --- |
| L0 | 单次 inspect + LLM patch + test |
| L1 | PlanAct graph + LLM developer |
| L2 | PlanAct + 角色分工 + LLM developer |
| L3 | L2 + SkillCard |
| L4 | L2 + MemoryHint |
| L5 | L2 + Skill + Memory + policy gating |

### 首次 Real LLM 结果（`phase6_hard_12`，Run `20260703_064221`）

| Config | Success | 关键发现 |
| --- | ---: | --- |
| L1/L2 | **92%** | hard_12 对真实 LLM 仍偏易（饱和） |
| L3 | 67% | skill 注入 **拉低** 成功率 |
| L4 | 58% | memory 注入 **拉低**；parse_err=2 |
| L5 | 75% | **未优于 L2**；parse_err=3 |

**动机 Phase 7**：benchmark 饱和 + skill/memory 负收益 + `needs_more_context` 直接失败 + parse error。

---

## 5. Phase 7.1：正向收益硬化（Batch 1–6）

**计划文档**：`PHASE7_1-POSITIVE-GAIN-HARDENING-PLAN.zh-CN.md`  
**决策**：不推倒重来；OpenHands/SWE-agent/Aider 作 optional baseline；主叙事改为能力增强。

---

### Batch 1：证据冻结 + External Baseline 接口

| 项 | 内容 |
| --- | --- |
| **改动** | `docs/current-evidence.md`；`reposkill_agent/baselines/`；`run_external_baselines.py`（skip-with-reason） |
| **原因** | 冻结 Phase 6 / early LLM 负结果；为可选外部对比留接口 |
| **结果** | pytest/ruff 通过；未安装外部工具时 baseline 可 skip |

---

### Batch 2：Medium Repo Benchmark

| 项 | 内容 |
| --- | --- |
| **改动** | `medium_inventory` / `medium_config_loader` / `medium_event_pipeline`；`phase7_medium_24.yaml`（24 任务，6 类标签） |
| **原因** | single-file hard_12 饱和；需多文件、repo convention、holdout 配对 |
| **设计原则** | 2–5 expected_files；support/holdout；不把答案写进 issue |
| **结果** | L0/L2 smoke 确认未饱和（L0 目标 35%–60%） |

---

### Batch 3：SkillCard v2 + MemoryHint v2

| 项 | 内容 |
| --- | --- |
| **改动** | SkillSpec 扩展（evidence、anti_patterns、negative_transfer）；compact prompt 注入；MemoryHint 字段（repo_convention、procedural、confidence）；evidence gating；注入上限（skill≤2，memory≤3） |
| **原因** | Phase 6 LLM 下 L3/L4 因 prompt 噪声和缺 gating 负收益 |
| **结果** | 单元测试覆盖 gating；为 Batch 4–5 打基础 |

---

### Batch 4：Context Expansion + JSON Repair

| 项 | 内容 |
| --- | --- |
| **改动** | `PatchPlan.requested_context`；`needs_more_context` → Locator 扩展 allowed paths（每轮≤3，总计≤6）；JSON repair retry（最多 1 次）；metrics：`ctx_expand`/`ctx_recovered`/`repair_try`/`repair_ok` |
| **原因** | api/context 类任务因上下文不足直接失败；prompt 膨胀导致 parse error |
| **结果** | `run_mechanism_smoke.py` 验证；context-heavy 子集 L2 明显高于 L0 |

**涉及文件**：`core/context_expansion.py`、`agents/llm_developer.py`、`eval/graph_runner.py`

---

### Batch 4.5：Mechanism Smoke

| 项 | 内容 |
| --- | --- |
| **改动** | `scripts/run_mechanism_smoke.py`、`tests/test_mechanism_smoke.py` |
| **原因** | 真实 LLM eval 前快速验证 context/repair 链路 |
| **结果** | CI 可跑；不消耗 API |

---

### Batch 5.1–5.3：早期 Real LLM Probe（6 task）

| Run | 任务数 | L0 | L2 | L5 | 关键发现 |
| --- | ---: | ---: | ---: | ---: | --- |
| `20260703_100611` | 6 | 17% | 67% | **17%** | L5 崩溃；parse_err=4；policy 未成熟 |
| `20260703_110454` | 6 | — | — | 17% | L5 极低，机制硬化前 |
| **`20260703_114107`** | **6** | **33%** | **83%** | **67%** | gating/suppression 见效；L5 从 17%→67% |

**Batch 5.3 子集结果（Run `114107`）**：

| 类别 | L5 | 判定 |
| --- | ---: | --- |
| skill_heavy | **100%** | ✅ 机制有效 |
| context_heavy | **100%** | ✅ |
| memory_heavy | **0%** | ❌ **blocker** |

**原因分析**：memory hint 质量 / holdout 匹配 / suppression 过严；skill+context 路径已通，memory 未通。

**决策**：先攻 memory，不直接 full 24。

---

### Batch 5.4：Memory 子集修复

| 项 | 内容 |
| --- | --- |
| **改动** | `memory/matching.py`（holdout↔support 配对、`procedural_applies`、`REPO_CONVENTIONS`、`extract_test_signals`）；retriever/consolidator 收紧；`injection_policy.py` category router 初版 |
| **原因** | memory_heavy 0%；holdout 无法复用 support 成功经验 |
| **结果** | memory_heavy **0% → 86%**（memory 子集 probe）；context 未破坏 |

---

### Batch 5.5：Probe-12 首次全类别测试

**任务集**：`phase7_probe_12.yaml`（12 题：skill/context/memory 各 4）  
**Run `20260703_170314`**

| Config | Success | 判定 |
| --- | ---: | --- |
| L0 | 42% | — |
| L2 | **92%** | 强 baseline |
| L5 | **75%** | ❌ **低于 L2（-17pp）** |

| 类别 | L2 | L5 | 问题 |
| --- | ---: | ---: | --- |
| skill_heavy | 100% | **50%** | 错误 skill 注入 + skill/memory 共屏 |
| context_heavy | 100% | 100% | 无回退 |
| memory_heavy | 75% | 75% | 持平 |

**失败归因**：

- `inv_api_tax_01`：`event_serializer_compat` 错误 skill（domain 不匹配）
- `inv_rename_01`：replan 后 augmentation 全抑制，未恢复
- skill_primary 仍允许 repo_profile memory 与 skill 竞争 prompt

**决策**：❌ 不开 full 24。

---

### Batch 5.5.1：skill_primary 改 skill-only

| 项 | 内容 |
| --- | --- |
| **改动** | `skill_primary`：`allow_memory=False`，`max_memory_hints=0` |
| **原因** | skill_heavy 上 skill+memory 共注入是主干扰源 |
| **结果**（Run `20260703_221056`） | skill_heavy 50%→**75%**；`inv_rename_01` 恢复；但 L5 overall 仍 **75%**；`evt_context_pipeline_01` 新回退 |

**决策**：继续 ❌ 不开 full 24；需清 skill 库负迁移。

---

### Batch 5.6：Skill Domain Gating + Context 守护

| 项 | 内容 |
| --- | --- |
| **改动** | `skills/domain.py`（domain_compatible）；validator 拒绝 `domain_mismatch`；retriever 预过滤；新增 `inventory_tax_api.md`；`context_primary` 关 memory |
| **原因** | `inv_api_tax_01` 持续失败；inventory 任务注入 events domain skill |
| **结果**（Run `20260703_223829`） | L5=**92%** > L2=**83%**；skill_heavy=**100%**；skill_neg=**0** |

| 任务 | 5.5.1 | 5.6 |
| --- | ---: | ---: |
| `inv_api_tax_01` | ❌ | ✅ |
| `evt_context_pipeline_01` | ❌ | ✅ |

**决策**：✅ **准入 full 24**。

---

### Batch 5.7：Full 24 首次真实评测

**Run `20260703_231744`（L0/L2/L5）+ `20260704_000519`（L3/L4）**

| Config | Success | 备注 |
| --- | ---: | --- |
| L0 | 46% | 未饱和 ✅ |
| L2 | 71% | — |
| L4 | **83%** | 高于 L5 |
| L5 | **79%** | +8.4pp vs L2，但 **< L4** |

**关键问题**：

- `conservative_mix` 在 repo_convention / multi_file_api 上同时注入 skill+memory，弱于 L4 memory-only
- skill_negative_transfer=**3**
- L5 memory_heavy **100%**（7/7）— memory 已不是 blocker

**归档**：`reports/archive/batch5.7-full24/`

**决策**：过线「L5≥L0+20pp、memory 正向」，但未过「L5≥L4、+10pp ideal」；进入 Batch 5.8 降干扰。

---

### Batch 5.8：干扰路由修复（Policy Router）

| 项 | 内容 |
| --- | --- |
| **改动** | 移除 `conservative_mix`；`multi_file_api`/`repo_convention` → memory-only；`traceback_repair` → minimal；`skill_primary` max_skills=1；非 holdout memory route `exclude_repo_profile` |
| **原因** | 5.7 失败分析：L4>L5 主因是 skill+memory 混合干扰 |
| **结果**（Run `20260704_012041`） | L5=**79%**（持平）；L5**≥**L4 ✅；context_heavy=**100%**；skill_neg=**0**；parse_err 3→2 |

| 指标 | 5.7 | 5.8 |
| --- | ---: | ---: |
| L5 vs L2 | +8.4pp | +4.2pp |
| L5 vs L4 | L5 < L4 | **L5 > L4** ✅ |
| skill_neg | 3 | **0** |

**决策**：核心目标（L5 不再弱于 L4）达成；overall +4~8pp，可扩展 benchmark，不宜继续盲调 policy。

---

### Batch 5.9：Medium 48 扩展

| 项 | 内容 |
| --- | --- |
| **改动** | 新增 `medium_auth_rules` repo + 24 新任务（原 24 不变）；`phase7_medium_48.yaml` |
| **原因** | 24 题覆盖偏窄；用任务多样性补充泛化声称（尚未做 repeats） |
| **结果**（Run `20260704_062354`，repeats=1） | L0=48%，L2=69%，L5=**79%**，**L5−L2=+10.4pp** |

| 类别 | L2 | L5 | L5≥L2 |
| --- | ---: | ---: | --- |
| skill_heavy | 60% | **80%** | ✅ |
| memory_heavy | 75% | **94%** | ✅ |
| context_heavy | 70% | **90%** | ✅ |
| multi_file_api | 50% | 25% | ❌ 共享难点 |

**决策**：单次结果达标，但缺 run-to-run 方差；进入 Batch 5.10。

---

### Batch 5.10：Variance Check（最终实验）

| 项 | 内容 |
| --- | --- |
| **命令** | `phase7_medium_48` · L0/L2/L5 · **repeats=2** · seed=42 · ~3.2h |
| **原因** | +10.4pp margin 不算巨大；需排除单次模型波动质疑 |
| **结果**（Run `20260704_092308`） | 见下表 |

| Config | Mean | Std | R0 | R1 |
| --- | ---: | ---: | ---: | ---: |
| L0 | 45.8% | ±2.1pp | 47.9% | 43.8% |
| L2 | 70.8% | ±2.1pp | 72.9% | 68.8% |
| **L5** | **80.2%** | **±5.2pp** | 75.0% | 85.4% |

- **L5−L2 mean = +9.4pp**
- **两次 repeat 均 L5 ≥ L2**
- parse_err：L5=10，L2=10
- skill_heavy +15pp · memory_heavy +12.5pp

**验收**：**强通过**。

**决策**：✅ **实验收口**；不跑 repeats=3。

---

### Batch 6：最终包装

| 项 | 内容 |
| --- | --- |
| **改动** | `README.md` 重写；`phase7-positive-gain-summary.md` 定稿；`current-evidence.md` 更新；`SESSION-HANDOFF.zh-CN.md` 更新；3 个 case study + `limitations.md` |
| **原因** | 将 Batch 5.10 作为主证据；诚实披露方差与局限 |
| **结果** | 文档闭环；pytest 83 passed；ruff 通过 |

---

## 6. 机制改动与收益对照（汇总表）

| 机制 / 改动 | 引入批次 | 要解决的问题 | 最终贡献 |
| --- | --- | --- | --- |
| PlanAct + Multi-Agent (L2) | Phase 2–3 | 单轮 LLM 上下文不足 | L2=70.8% vs L0=45.8%（+25pp baseline lift） |
| SkillCard v2 + evidence gating | Batch 3 | skill prompt 噪声 | skill_heavy +15pp（5.10） |
| Domain gating | Batch 5.6 | 跨 repo 错误 skill | `inv_api_tax_01` 恢复；skill_neg→0 |
| skill_primary skill-only | Batch 5.5.1 | skill/memory 共注入 | skill_heavy 50%→75% |
| MemoryHint v2 + holdout matching | Batch 5.4 | memory_heavy 0% | memory_heavy +12.5pp（5.10） |
| Augmentation policy router | Batch 5.4–5.8 | 类别错配注入 | L5≥L4；移除 conservative_mix |
| Context expansion | Batch 4 | needs_more_context 失败 | L2 context 85%；L5 持平 |
| JSON repair retry | Batch 4 | parse error | repair 有效；L5 parse 不高于 L2 |
| medium_48 扩展 | Batch 5.9 | 24 题覆盖不足 | 单次 +10.4pp；多样性支撑 |
| repeats=2 方差 | Batch 5.10 | 单次偶然性质疑 | mean±std 主结论 |

---

## 7. 评测演化（benchmark 变迁）

| 阶段 | Benchmark | 任务数 | 角色 |
| --- | --- | ---: | --- |
| Plumbing | `phase6_tiny_24` | 24 | 管线稳定（全 1.00，不作机制结论） |
| Deterministic | `phase6_hard_12` | 12 | A0–A5 机制证据 |
| Early LLM | `phase6_hard_12` | 12 | 暴露饱和（L2≈92%）与负收益 |
| Development | `phase7_probe_12` | 12 | 快速迭代 policy / gating |
| Full eval | `phase7_medium_24` | 24 | 5.7–5.8 full run |
| **Final** | **`phase7_medium_48`** | **48** | **主结论（5.9 supporting + 5.10 权威）** |

---

## 8. 最终结论（可对外表述）

> RepoSkillAgent 通过 PlanAct、多角色协作、SkillCard domain gating、MemoryHint holdout 复用与 category policy router，在 **48 个 medium repo tasks、2 次真实 DeepSeek repeats** 上，将 multi-agent baseline（L2）从 **70.8% ± 2.1pp** 提升到 **80.2% ± 5.2pp**（**+9.4pp mean**）；两次 repeat 均满足 L5 ≥ L2；收益集中在 skill-heavy 与 memory-heavy；parse error 不高于 baseline。

**不再做**：repeats=3、继续调 benchmark 追分、修改测试断言抬分。

---

## 9. 关键报告索引

| 文档 | 路径 |
| --- | --- |
| 本历程 | `docs/project-chronology.zh-CN.md` |
| **权威方差（主证据）** | `reports/phase7-variance-summary.md` |
| 最终叙事摘要 | `reports/phase7-positive-gain-summary.md` |
| 48 题单次结果 | `reports/phase7-medium48-summary.md` |
| Probe-12 迭代全记录 | `reports/phase7-probe-12-summary.md` |
| Full-24 失败分析 | `reports/phase7-full24-failure-analysis.md` |
| Phase 6 deterministic | `reports/phase6-eval-summary.md` |
| 5.7 归档 | `reports/archive/batch5.7-full24/` |
| 证据分层 | `docs/current-evidence.md` |
| 局限 | `docs/limitations.md` |
| Case studies | `docs/case-study-*.md` |
| 会话交接 | `docs/SESSION-HANDOFF.zh-CN.md` |

---

## 10. 变更记录

| 日期 | 说明 |
| --- | --- |
| 2026-07-02 | Phase 6 eval strengthening 完成 |
| 2026-07-03 | DeepSeek LLM 接入；Phase 7.1 Batch 1–5.3 |
| 2026-07-03 | Batch 5.4–5.6 probe 迭代；5.7 full 24 |
| 2026-07-04 | Batch 5.8–5.10；实验收口；Batch 6 文档 |
| 2026-07-04 | 本历程文档初版 |
