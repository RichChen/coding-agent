# Phase 7.1 Positive-Gain Hardening Plan

> 用途：交给 Cursor Composer 执行。  
> 主目标：继续当前 RepoSkillAgent 项目，不推倒重来；把 OpenHands SDK / SWE-agent / Aider 作为底座或 baseline 接入，并把真实 DeepSeek LLM 下的 PlanAct + MultiAgent + Skill + Memory 做出正向收益。  
> 运行环境：conda env `coding-agent`。  
> 安全要求：真实 API key 只从 `.env` 或本地环境变量读取，严禁写入代码、文档、trace、report。

---

## 0. 决策结论

本阶段不 clone 大型开源项目后重写，也不把当前项目废掉。

采用折中方案：

```text
RepoSkillAgent 继续作为能力增强层和实验主仓库
OpenHands SDK 作为可选 runtime / workspace 底座
SWE-agent / Aider 作为可选外部 baseline 或参考实现
DeepSeek 真实 LLM eval 作为最终正向收益证据
```

项目主叙事从“我有一个 eval framework”调整为：

> 我做了一个真实 LLM Coding Agent 能力增强系统，通过 PlanAct、多 Agent 分工、可验证 Skill、可复用 Memory，让模型在 repo 任务上比 vanilla LLM / vanilla agent 更可靠。

评测仍然重要，但它只是证据，不是主角。

---

## 1. 研究契约

### 1.1 假设

在更接近真实 repo 的 medium tasks 上，以下机制会带来真实 LLM 成功率提升：

- PlanAct + context expansion 能把 `needs_more_context` 转化为可恢复流程。
- MultiAgent 的 Locator/QA 能提供更好的文件定位、失败归因和二次修复上下文。
- SkillCard v2 能把常见代码修改模式压缩成可验证、低噪声的工作流。
- MemoryHint v2 能在同一 repo / 同一任务族中复用 repo convention 和成功修复经验。
- L5 full system 应显著优于 L0 single LLM 和 L2 planner+multi baseline。

### 1.2 核心比较

至少比较：

| Config | 含义 | 必须 |
| --- | --- | --- |
| `L0_llm_single` | 单次 inspect + LLM patch + test | 是 |
| `L1_llm_planner` | PlanAct single graph + LLM developer | 是 |
| `L2_llm_multi` | PlanAct + role agents + LLM developer | 是 |
| `L3_llm_skill_v2` | L2 + SkillCard v2 | 是 |
| `L4_llm_memory_v2` | L2 + MemoryHint v2 | 是 |
| `L5_llm_full_v2` | L2 + SkillCard v2 + MemoryHint v2 | 是 |
| `B_openhands_sdk` | OpenHands SDK runtime / vanilla baseline | 可选 |
| `B_swe_agent` | SWE-agent external baseline | 可选 |
| `B_aider` | Aider external baseline | 可选 |

可选 baseline 不应阻塞主线。若依赖、网络、运行成本过高，可实现 skip-with-reason，并在报告里注明。

### 1.3 成功信号

目标不是“所有配置都好看”，而是 L5 在机制适配的任务上明显胜出。

建议验收线：

```text
phase7_medium_24, repeats=1:
L5_full_v2 >= L2_multi + 15 percentage points
L5_full_v2 >= L0_single + 20 percentage points
Skill-heavy subset: L3/L5 > L2
Memory-heavy subset: L4/L5 > L2
Context-heavy subset: L2/L5 > L0/L1
```

质量约束：

```text
llm_parse_error_total 不应显著高于 L2
patch_rejected_total 可以存在，但必须可解释
L5 平均 LLM calls 不应超过 L2 的 2.5x
失败样本必须有 failure taxonomy
报告不得包含 API key 或完整 prompt
```

### 1.4 失败信号

如果出现以下情况，不要包装成成功：

- L5 不高于 L2，且没有明确子集收益。
- SkillCard v2 增加 prompt 噪声，导致 parse error 或错误 patch 增多。
- MemoryHint v2 命中过期/错误经验，出现明显 negative transfer。
- External baseline 跑不通且没有 skip reason。
- 为了让 L5 过而修改 benchmark 期望、测试断言或泄露答案。

---

## 2. 外部项目接入边界

### 2.1 OpenHands SDK

推荐用途：

- 作为可选 runtime / workspace adapter。
- 验证 RepoSkillAgent 的 capability layer 能跑在更真实的执行底座上。

不推荐：

- clone OpenHands 全仓库后重写本项目。
- 引入 UI、server、Docker 平台细节作为主线。

执行要求：

- 新增 adapter 或 baseline 层时必须保持 optional dependency。
- 如果 SDK API 变化或未安装，测试应 skip，不应破坏主测试。
- 上层仍依赖 `WorkspaceAdapter` 或明确的 baseline interface。

参考：

- https://github.com/OpenHands/OpenHands
- https://github.com/OpenHands/software-agent-sdk

### 2.2 SWE-agent

推荐用途：

- 作为外部 issue-to-patch baseline。
- 借鉴 trajectory / repair loop / SWE-bench 风格接口。

不推荐：

- 把 RepoSkillAgent 变成 SWE-agent wrapper。

执行要求：

- 不 vendor SWE-agent 源码。
- 通过命令行 adapter 或文档化 baseline runner 接入。
- 如果本地没有 SWE-agent，输出 skip reason。

参考：

- https://github.com/SWE-agent/SWE-agent

### 2.3 Aider

推荐用途：

- 作为 vanilla pair-programming baseline。
- 借鉴 repo-map / edit strategy / CLI workflow。

不推荐：

- 把 Aider 作为多 Agent / memory 主体。

执行要求：

- 不 vendor Aider 源码。
- 通过外部命令 runner 接入，保留日志摘要、diff、pytest result。

参考：

- https://github.com/Aider-AI/aider

---

## 3. 实施阶段

### Phase 7.1.0：冻结当前证据与健康检查

目标：保留当前 Phase 6 / real LLM 结果，不覆盖已有报告。

任务：

- 确认以下文件存在：
  - `reports/phase6-eval-summary.md`
  - `reports/llm/20260703_064221/llm-ablation-summary.md`
  - `docs/evaluation-contract.md`
- 新增或更新 `docs/current-evidence.md`：
  - deterministic 证据摘要；
  - real LLM 证据摘要；
  - 当前不足：L3/L4/L5 在真实 LLM 下未正向。
- 跑：

```powershell
python -m pytest -o cache_dir=.tmp/pytest_cache --basetemp=.tmp/pytest
python -m ruff check reposkill_agent tests scripts benchmarks
```

验收：

- pytest / ruff 通过。
- 不删除旧 reports。

---

### Phase 7.1.1：External Baseline Interface

目标：把外部项目作为 baseline 接入，而不是接管当前项目。

建议新增：

```text
reposkill_agent/baselines/
  __init__.py
  contracts.py
  vanilla_deepseek.py
  external_command.py
  openhands_sdk.py
  swe_agent.py
  aider.py
scripts/run_external_baselines.py
tests/test_external_baselines.py
```

`contracts.py` 建议结构：

```python
class BaselineRunRequest(BaseModel):
    task_id: str
    issue: str
    repo_path: Path
    test_command: str
    expected_files: list[str]
    output_dir: Path

class BaselineRunResult(BaseModel):
    name: str
    task_id: str
    status: Literal["success", "failure", "skipped", "error"]
    skip_reason: str = ""
    test_passed: bool = False
    wall_time_ms: float = 0.0
    llm_calls: int = 0
    diff_summary: str = ""
    report_path: str = ""
```

实现要求：

- `vanilla_deepseek.py` 可以复用现有 `ModelClient`，作为明确 baseline。
- `external_command.py` 封装通用外部命令 baseline：
  - 工作目录隔离；
  - timeout；
  - stdout/stderr 摘要；
  - 运行 pytest；
  - 生成 diff summary。
- `openhands_sdk.py / swe_agent.py / aider.py` 先做 optional adapter：
  - 未安装或未配置时返回 `status="skipped"`；
  - 不影响主测试；
  - 不下载依赖；
  - 不写 API key。
- 新脚本支持：

```powershell
python scripts/run_external_baselines.py --tasks benchmarks/tasks/phase7_medium_24.yaml --baseline vanilla_deepseek --limit 3
python scripts/run_external_baselines.py --tasks benchmarks/tasks/phase7_medium_24.yaml --baseline aider --limit 3
```

验收：

- 无外部依赖时，optional baselines 可以 skip。
- `vanilla_deepseek` 至少能在 mock client 下测试。
- 报告写入 `reports/external_baselines/<run_id>/summary.md`。

---

### Phase 7.1.2：Medium Repo Benchmark

目标：新增更能体现机制价值的任务集，避免 single-file toy 饱和。

建议新增 3 个 medium synthetic repos，先不要下载外部仓库，降低执行风险：

```text
benchmarks/repos/medium_inventory/
benchmarks/repos/medium_config_loader/
benchmarks/repos/medium_event_pipeline/
benchmarks/tasks/phase7_medium_24.yaml
```

任务设计原则：

- 每个 repo 8 个任务，共 24 个任务。
- 每个任务允许 2-5 个 `expected_files`。
- 每个 repo 包含 2-3 个 support-style 任务和 5-6 个 holdout-style 任务。
- 任务要分为：
  - `context_heavy`
  - `skill_heavy`
  - `memory_heavy`
  - `multi_file_api`
  - `traceback_repair`
  - `repo_convention`
- 不要把答案写进 issue。
- 测试应能区分“只改表面”和“理解 repo convention”。

示例 repo 方向：

#### `medium_inventory`

模块：

```text
inventory/models.py
inventory/pricing.py
inventory/discounts.py
inventory/api.py
inventory/validators.py
tests/
```

任务类型：

- API signature migration：`calculate_total(items, region)` 改为支持 tax profile。
- 跨文件 rename：`sku_id` -> `item_id`。
- repo convention：错误时返回 `Result(ok=False, error=...)`，不是抛异常。
- regression：折扣为 0、空购物车、未知 region。

#### `medium_config_loader`

模块：

```text
config_loader/sources.py
config_loader/schema.py
config_loader/merge.py
config_loader/env.py
config_loader/api.py
tests/
```

任务类型：

- 默认值 merge 顺序错误。
- env var override 规则。
- typed schema validation。
- config key alias migration。

#### `medium_event_pipeline`

模块：

```text
events/message.py
events/registry.py
events/handlers.py
events/serializer.py
events/pipeline.py
tests/
```

任务类型：

- handler registry API 变化。
- serialization backward compatibility。
- retry policy convention。
- traceback-driven bug fix。

验收：

- `python -m pytest` 能跑项目测试。
- 新 benchmark 的 L0 不应接近满分。目标 L0 在 35%-60% 区间。
- 不依赖网络和外部服务。

---

### Phase 7.1.3：SkillCard v2

目标：让 skill 真正提升 LLM，而不是增加 prompt 噪声。

建议修改：

```text
reposkill_agent/skills/models.py
reposkill_agent/skills/validator.py
reposkill_agent/skills/retriever.py
reposkill_agent/llm/prompts.py
reposkill_agent/agents/llm_developer.py
```

SkillCard v2 字段建议：

```python
class SkillSpec(BaseModel):
    id: str
    name: str
    version: str
    purpose: str
    pattern: str
    required_evidence: list[str]
    edit_recipe: list[str]
    anti_patterns: list[str]
    verifier: str
    applies_when: list[str]
    not_applicable_when: list[str]
    success_count: int = 0
    failure_count: int = 0
    negative_transfer_notes: list[str] = []
```

Prompt 注入格式必须短：

```text
SkillCard:
id:
pattern:
evidence:
recipe:
avoid:
verify:
```

Gating 规则：

- 最多注入 2 个 skill。
- `required_evidence` 必须被 issue、test output、locator matches 或 repo files 满足。
- 如果 evidence 不足，不注入。
- 如果 skill 最近 negative transfer 高，不注入或降权。
- 在 report 中记录：
  - `skill_candidate_count`
  - `skill_injected_count`
  - `skill_gated_count`
  - `skill_negative_transfer_count`

验收：

- 新增单元测试覆盖 evidence gating。
- L3/L5 prompt 长度不要显著膨胀。

---

### Phase 7.1.4：MemoryHint v2

目标：把 memory 变成低噪声、可行动经验。

建议修改：

```text
reposkill_agent/memory/
reposkill_agent/agents/memory_curator.py
reposkill_agent/llm/prompts.py
```

MemoryHint v2 字段建议：

```python
class MemoryHint(BaseModel):
    type: Literal["repo_profile", "episodic", "procedural"]
    source_task_id: str
    confidence: float
    applies_when: list[str]
    likely_files: list[str]
    successful_pattern: str
    repo_convention: str = ""
    warning: str = ""
```

注入规则：

- 最多注入 3 条 hint。
- 优先 repo_profile + procedural。
- 低 confidence 只作为 hint，不进入 allowed paths 硬约束。
- memory 必须带 source task id。
- 失败任务不能直接沉淀成 procedural memory。

报告指标：

```text
memory_candidate_count
memory_injected_count
memory_useful_count
memory_stale_or_wrong_count
memory_source_task_ids
```

验收：

- seeded memory 在 `phase7_medium_24` 上应体现收益。
- 至少产出 1 个 case study：第一次失败/低效，后续因 memory 成功或更快。

---

### Phase 7.1.5：Context Expansion + Replan

目标：把真实 LLM 的 `needs_more_context` 变成 PlanAct / MultiAgent 的收益点。

当前问题：

```text
LLMDeveloperAgent 返回 needs_more_context 后，很多 run 直接失败。
```

目标流程：

```text
Developer: needs_more_context / requested_context
Manager: replan
Locator: expand files / symbols / callers / tests
Developer: second attempt with richer context
QA: verify
```

建议修改：

- `PatchPlan` schema 增加可选字段：

```python
requested_context: list[str] = []
```

- `LLMDeveloperAgent` 在 `needs_more_context` 时返回 requested context。
- `LocatorAgent` 支持根据 requested context 扩展：
  - caller files；
  - tests；
  - same package modules；
  - config/schema files。
- `TaskGraphRunner` 允许把 locator 扩展文件加入 `allowed_paths`，但必须记录 reason。
- 限制：
  - 每轮最多新增 3 个 allowed paths；
  - 总 allowed paths 不超过 6；
  - 不允许全仓库放开。

新增指标：

```text
context_expansion_count
allowed_path_added_count
needs_more_context_recovered_count
```

验收：

- context-heavy subset 上 L2/L5 应明显高于 L0。
- 至少 2 个任务展示 `needs_more_context -> locator expansion -> pass`。

---

### Phase 7.1.6：JSON Repair Retry

目标：降低 Skill/Memory 注入后 parse error 对 L5 的伤害。

要求：

- 对 `llm_parse_error` 最多做 1 次 repair retry。
- repair prompt 只包含：
  - schema；
  - raw response preview；
  - allowed paths；
  - 不包含 API key；
  - 不写完整原始 prompt 到 report。
- retry 结果仍必须通过 `PatchPlan` schema 和 path scope。

指标：

```text
llm_parse_error_total
llm_parse_repair_attempt_total
llm_parse_repair_success_total
```

验收：

- L4/L5 parse error 明显下降。
- 不引入越权 patch。

---

### Phase 7.1.7：Real LLM Positive-Gain Eval

目标：用真实 DeepSeek 跑出正向收益报告。

Smoke：

```powershell
python scripts/run_llm_ablation.py --tasks benchmarks/tasks/phase7_medium_24.yaml --limit 3 --repeats 1 --seed 42
```

Full：

```powershell
python scripts/run_llm_ablation.py --tasks benchmarks/tasks/phase7_medium_24.yaml --repeats 1 --seed 42
```

Seeded memory：

```powershell
python scripts/run_llm_ablation.py --tasks benchmarks/tasks/phase7_medium_24.yaml --repeats 1 --seed 42 --seed-memory
```

如果成本允许，对关键配置 repeats=3：

```powershell
python scripts/run_llm_ablation.py --tasks benchmarks/tasks/phase7_medium_24.yaml --repeats 3 --seed 42 --configs L0_llm_single,L2_llm_multi,L5_llm_full_v2
```

需要生成：

```text
reports/llm/<run_id>/llm-ablation-summary.md
reports/llm/<run_id>/llm-ablation-summary.json
reports/phase7-positive-gain-summary.md
```

`reports/phase7-positive-gain-summary.md` 必须包含：

- config 总表；
- 按 task category 分组；
- skill-heavy / memory-heavy / context-heavy 子集收益；
- parse error / repair success；
- context expansion recovery；
- 失败案例；
- 正向案例；
- 是否满足 Phase 7 README 包装条件。

---

### Phase 7.1.8：README 与展示叙事

目标：把项目从“eval framework”改写成“真实 LLM 能力增强系统”。

README 第一屏建议结构：

```text
RepoSkillAgent
一句话定位
Why this project
Architecture
What is enhanced over vanilla LLM
Real LLM results
How to reproduce
Honest limitations
```

必须突出：

- 真实 DeepSeek LLM，而不是 mock。
- L5 相比 L0/L2 的正向收益。
- Skill/Memory 不是简单 prompt，而是 gated + validated + measured。
- OpenHands/SWE-agent/Aider 是 baseline / runtime reference，不是项目主体。

建议新增：

```text
docs/design.md
docs/research-notes.md
docs/case-study-context-expansion.md
docs/case-study-memory-reuse.md
docs/external-baselines.md
```

---

## 4. Composer 执行顺序

请严格按顺序执行，不要一口气改完所有东西。

### Batch 1：文档与 baseline interface

```text
1. 新增 docs/current-evidence.md
2. 新增 reposkill_agent/baselines/ 基础接口
3. 新增 scripts/run_external_baselines.py
4. optional external baselines 先实现 skip-with-reason
5. pytest / ruff
```

### Batch 2：medium benchmark

```text
1. 新增 3 个 medium repos
2. 新增 phase7_medium_24.yaml
3. 保证每个 repo 独立 pytest 可跑
4. 先跑 L0/L2 smoke，确认 baseline 没饱和
```

### Batch 3：SkillCard v2 + MemoryHint v2

```text
1. 扩展 SkillSpec
2. 改 skill library markdown
3. 实现 evidence gating
4. 实现 compact skill prompt
5. 实现 compact memory hint
6. 增加单元测试
```

### Batch 4：Context expansion + JSON repair

```text
1. PatchPlan 增加 requested_context
2. LLMDeveloperAgent 返回 needs_more_context payload
3. Locator 扩展 allowed paths
4. TaskGraphRunner 记录 context expansion 指标
5. 增加 parse repair retry
6. 单元测试覆盖
```

### Batch 5：真实 DeepSeek full eval

```text
1. 不使用 --mock-llm
2. 从 .env 读取 DeepSeek 配置
3. 先 limit=3 smoke
4. 再 full 24 tasks
5. 必要时 seeded memory
6. 生成 phase7-positive-gain-summary.md
```

### Batch 6：README / docs 收口

```text
1. README 第一屏重写
2. 增加 architecture diagram
3. 增加 positive-gain result table
4. 增加 case studies
5. 明确 limitations
```

---

## 5. 安全与合规

禁止：

- 打印 `.env`。
- 写入 API key。
- vendor OpenHands / SWE-agent / Aider 源码。
- 为结果修改测试期望。
- 删除旧 reports。
- 把 full prompt 或完整 LLM raw response 写入公开 report。

允许：

- 在 report 中写 prompt length、token estimate、error type。
- 在 optional baseline 未安装时 skip。
- 为降低成本先跑 limit=3。
- 使用 mock client 做单元测试。

---

## 6. 直接给 Composer 的提示词

```text
请执行 `PHASE7_1-POSITIVE-GAIN-HARDENING-PLAN.zh-CN.md`。

目标：不要推倒重来，继续当前 RepoSkillAgent；把 OpenHands SDK / SWE-agent / Aider 作为 optional runtime/baseline 接入；重点把真实 DeepSeek LLM 下的 PlanAct + MultiAgent + Skill + Memory 做出正向收益。

优先执行 Batch 1 和 Batch 2：
1. 新增 docs/current-evidence.md，总结当前 deterministic 和 real LLM 证据。
2. 新增 reposkill_agent/baselines/ 与 scripts/run_external_baselines.py；OpenHands/SWE-agent/Aider 先实现 optional skip-with-reason，不要下载或 vendor 源码。
3. 新增 phase7_medium_24 benchmark，包含 3 个 medium synthetic repos，每个 repo 8 个任务，多文件、repo convention、context-heavy、skill-heavy、memory-heavy。
4. 跑 pytest 和 ruff。
5. 先用 mock 或 L0/L2 smoke 确认 benchmark 没有 baseline 饱和。

严禁打印或写入 API key。真实 DeepSeek eval 等 Batch 3/4 完成后再跑。
```
