# RepoSkillAgent 从零开始项目计划

> 目标：面向字节类 Agent 研发实习岗位，构建一个以 `PlanAct + MultiAgent + Skill + Memory` 为主线的 repo 任务 Agent 项目。  
> 底座：优先使用 OpenHands Software Agent SDK，不从零复刻 coding-harness 的 harness/eval/trace/policy 细节。  
> 交付对象：可直接交给 Cursor Composer 或其他执行侧 AI 分阶段实现。

---

## 0. 项目一句话

RepoSkillAgent 是一个面向小规模代码仓库任务的能力型 Agent 原型：它以 OpenHands SDK 提供的代码执行/工作区能力为底座，在其上实现结构化任务图规划、角色化多 Agent 协作、可验证 Skill Library、长期 Memory，并用 A/B 评测证明这些能力机制是否真的提升任务成功率、成本和可靠性。

旧项目 `coding-harness` 负责证明“Agent 基础设施可测、可控、可回放”。  
新项目 RepoSkillAgent 负责证明“Agent 能拆任务、会分工、会复用技能、会从成功/失败中沉淀经验”。

---

## 1. 明确边界

### 1.1 必须做

- 使用 OpenHands SDK 作为 coding agent/workspace/tool execution 底座。
- 实现一个轻量 `TaskGraphPlanner`，输出结构化任务图，而不是只输出自然语言 plan。
- 实现 3 到 5 个角色 Agent，至少包括：
  - `ManagerAgent`：规划、调度、replan、合并结论。
  - `LocatorAgent`：定位相关文件、符号、失败原因。
  - `DeveloperAgent`：生成补丁。
  - `QAAgent`：运行测试、审查 diff、分类失败。
  - `MemoryCuratorAgent`：从成功/失败轨迹中抽取可复用经验。
- 实现 Skill Library：
  - skill 有 metadata、适用条件、输入输出契约、验证方式、版本和失败记录。
  - skill 检索后必须经过适配/验证，不能盲目注入。
- 实现 Memory System：
  - episodic memory：任务轨迹、错误、补丁、测试结果。
  - procedural memory：从成功任务中沉淀的工作流/skill 使用模式。
  - repo profile memory：仓库结构、测试命令、风格约定、常见坑。
- 做小规模 repo 任务 A/B：
  - single-agent vs multi-agent
  - no skill vs skill retrieval
  - no memory vs memory
  - static plan vs replan

### 1.2 暂时不做

- 不做完整企业 Agent OS。
- 不做复杂 UI。
- 不复刻完整 SWE-bench pipeline。
- 不做分布式 worker、消息总线、Docker 隔离平台。
- 不做复杂多模型路由。
- 不把重点放在 harness 白名单、sandbox、trace viewer 等旧项目已有内容。
- 不直接 fork OpenHands 全量产品做二次包装；优先把 OpenHands SDK 包在 adapter 后面。

---

## 2. 论文与思想映射

这些 PDF 应放在项目根目录，方便执行侧 AI/人类随时查阅。

| 本地文件 | 论文/项目 | 借鉴点 | 项目落点 |
| --- | --- | --- | --- |
| `paper-2406.11638-MASAI.pdf` | MASAI: Modular Architecture for Software-engineering AI Agents | 将软件工程任务拆给不同子 Agent，减少单轨迹上下文污染 | `Manager / Locator / Developer / QA` 角色设计 |
| `paper-2411.04468-Magentic-One.pdf` | Magentic-One | Orchestrator 计划、追踪进度、replan、调度 specialist agents | `ManagerAgent` 调度循环 |
| `paper-2603.15401-SWE-Skills-Bench.pdf` | SWE-Skills-Bench | Skill 不一定有效，需验证 skill 适用性和负迁移 | Skill metadata、validator、A/B 指标 |
| `paper-2602.02474-MemSkill.pdf` | MemSkill | 把 memory 操作本身当成可演化 skill | `MemoryCuratorAgent` 和 memory skill |
| `paper-2409.07429-Agent-Workflow-Memory.pdf` | Agent Workflow Memory | 从历史成功轨迹中归纳 workflow memory | procedural memory 抽取与检索 |
| `paper-2602.16666-Agent-Reliability.pdf` | Towards a Science of AI Agent Reliability | success 之外评估 consistency、robustness、predictability | 多 seed/扰动评测与可靠性报告 |
| `paper-2602.02660-MARS.pdf` | MARS: Modular Agent with Reflective Search | budget-aware planning、reflective memory、模块化构造 | 后续增强版 planner/memory |

---

## 3. 技术选型

### 3.1 推荐主栈

- Language：Python 3.11+
- Agent 底座：OpenHands Software Agent SDK
- 数据模型：Pydantic
- 本地存储：
  - MVP：JSONL + SQLite
  - 可选增强：Chroma/Qdrant 或 Mem0 作为 memory backend
- 测试：pytest
- CLI：Typer 或 argparse
- 日志/trace：JSONL，先保持简单可 grep
- 配置：YAML + 环境变量

### 3.2 OpenHands 适配策略

创建 `OpenHandsAdapter`，屏蔽具体 SDK 调用细节。

要求：

- 上层只依赖统一接口：
  - `inspect_repo(task)`
  - `run_command(command)`
  - `apply_patch(patch)`
  - `read_file(path)`
  - `list_files(pattern)`
  - `run_tests(test_command)`
  - `produce_diff()`
- 如果 OpenHands SDK API 变化，只改 adapter。
- 单元测试中允许用 fake adapter，不强依赖真实 LLM/API。

---

## 4. 建议目录结构

```text
reposkill-agent/
  README.md
  pyproject.toml
  configs/
    default.yaml
    ablation.yaml
  reposkill_agent/
    __init__.py
    adapters/
      openhands_adapter.py
      fake_adapter.py
    core/
      task_graph.py
      planner.py
      orchestrator.py
      contracts.py
      trace.py
    agents/
      manager.py
      locator.py
      developer.py
      qa.py
      memory_curator.py
    skills/
      registry.py
      retriever.py
      validator.py
      models.py
      library/
        fix_import_error.md
        add_regression_test.md
        rename_symbol_across_files.md
    memory/
      episodic.py
      procedural.py
      repo_profile.py
      consolidator.py
      retriever.py
    eval/
      task_spec.py
      runner.py
      metrics.py
      ablation.py
      report.py
  benchmarks/
    tasks/
      tiny_python_tasks.yaml
    repos/
      README.md
  scripts/
    run_baseline.py
    run_ablation.py
    summarize_results.py
  traces/
    .gitkeep
  docs/
    design.md
    research-notes.md
    evaluation-contract.md
```

---

## 5. 核心数据结构

### 5.1 TaskGraph

```python
class TaskNode(BaseModel):
    id: str
    goal: str
    owner: Literal["manager", "locator", "developer", "qa", "memory_curator"]
    dependencies: list[str] = []
    expected_artifact: str
    verifier: str | None = None
    status: Literal["pending", "running", "passed", "failed", "skipped"] = "pending"
```

### 5.2 Skill

```python
class SkillSpec(BaseModel):
    id: str
    name: str
    version: str
    purpose: str
    applies_when: list[str]
    not_applicable_when: list[str]
    required_context: list[str]
    procedure: str
    verifier: str
    success_count: int = 0
    failure_count: int = 0
    negative_transfer_notes: list[str] = []
```

### 5.3 Memory

```python
class EpisodicMemory(BaseModel):
    task_id: str
    repo_fingerprint: str
    issue_summary: str
    plan_summary: str
    actions: list[dict]
    final_diff_summary: str
    tests: list[dict]
    outcome: Literal["success", "failure"]
    failure_type: str | None = None
```

```python
class ProceduralMemory(BaseModel):
    id: str
    source_task_ids: list[str]
    pattern: str
    reusable_workflow: list[str]
    applies_when: list[str]
    verifier: str
    confidence: float
```

---

## 6. 分阶段执行计划

### Phase 0：项目初始化

目标：搭好最小工程骨架，不实现复杂能力。

任务：

- 创建 Python package、`pyproject.toml`、pytest、ruff/black 或等价工具。
- 创建 README，写清项目定位和不做什么。
- 创建 fake adapter，保证无 LLM/API key 也能跑单测。
- 创建最小 `TaskSpec` 和 `TraceEvent`。

验收：

- `pytest` 通过。
- `python -m reposkill_agent --help` 或等价 CLI 可运行。

### Phase 1：OpenHands single-agent baseline

目标：先有一个可跑的 single-agent baseline，作为后续 A/B 的锚点。

任务：

- 实现 `OpenHandsAdapter`。
- 支持加载一个 tiny repo task。
- 让 single-agent 完成：读 issue、修改文件、运行测试、输出 diff、写 trace。

验收：

- 至少 3 个 toy repo task 可以跑通。
- 每次运行生成 JSONL trace。
- baseline 指标包含 success、steps、tokens/cost 占位、wall time、test result。

### Phase 2：TaskGraphPlanner + PlanAct loop

目标：从自然语言任务生成结构化任务图，并在执行中 observe/replan。

任务：

- 实现 `TaskGraphPlanner`。
- 支持 `plan -> execute node -> observe -> optional replan`。
- replan 次数设上限，默认 1 到 2 次。
- 每个 node 必须有 expected artifact 和 verifier。

验收：

- task graph 写入 trace。
- 失败时能定位失败节点。
- `static plan` 与 `replan` 可通过配置开关做 A/B。

### Phase 3：Role-based Multi-Agent

目标：实现少量清晰角色，不做大而全群聊。

任务：

- `ManagerAgent` 负责调度 task graph。
- `LocatorAgent` 输出相关文件/符号/错误假设。
- `DeveloperAgent` 只基于 locator 输出和上下文生成补丁。
- `QAAgent` 运行测试、审查 diff、给失败分类。
- 所有 agent 输出必须是结构化对象，不只写自然语言。

验收：

- `single-agent` 与 `multi-agent` 可切换。
- multi-agent trace 中能看到角色交接。
- QA 能把失败至少分成：定位错误、补丁错误、测试命令错误、上下文不足、skill/memory 误导。

### Phase 4：Skill Library

目标：实现可检索、可验证、可统计负迁移的 skill。

任务：

- 手写 3 到 5 个初始 skill：
  - fix import/module error
  - add regression test before fix
  - rename symbol across files
  - update API signature and callers
  - inspect failing pytest traceback
- 实现 skill retriever：
  - MVP 可用 BM25/关键词。
  - 后续可接 embedding。
- 实现 skill validator：
  - 检查 applies_when/not_applicable_when。
  - 检查 required_context 是否满足。
  - 记录 skill 是否带来成功或负迁移。

验收：

- `no skill` 与 `skill retrieval` 可 A/B。
- 报告 skill hit rate、validated hit rate、negative transfer count。
- skill 失败不会直接污染 procedural memory。

### Phase 5：Memory System

目标：让 Agent 从历史任务中沉淀经验，但避免“记错比不记更糟”。

任务：

- 每次任务结束写 episodic memory。
- 成功任务经 `MemoryCuratorAgent` 抽取 procedural memory。
- 为每个 repo 维护 repo profile：
  - 测试命令
  - 目录结构
  - 常见模块路径
  - 风格约定
- memory retrieval 必须带 confidence 和 source task id。
- 低 confidence memory 只作为 hint，不作为硬约束。

验收：

- `no memory` 与 `memory` 可 A/B。
- 报告 memory retrieval count、useful memory count、stale/wrong memory count。
- 至少能展示 1 个“第一次失败/低效，第二次因 procedural memory 更快成功”的案例。

### Phase 6：Evaluation Contract

目标：用小规模 repo 任务证明机制价值，而不是讲 demo。

任务：

- 构建 20 到 40 个 tiny repo tasks。
- 每个 task 有：
  - issue 描述
  - 初始仓库状态
  - 期望测试命令
  - hidden/visible assertions
  - failure taxonomy label
- 实现 ablation runner。
- 每个配置至少跑 3 次或 3 个 seed。

推荐 ablation：

| 配置 | Planner | Multi-Agent | Skill | Memory |
| --- | --- | --- | --- | --- |
| A0 baseline | 否 | 否 | 否 | 否 |
| A1 planner | 是 | 否 | 否 | 否 |
| A2 multi-agent | 是 | 是 | 否 | 否 |
| A3 skill | 是 | 是 | 是 | 否 |
| A4 memory | 是 | 是 | 否 | 是 |
| A5 full | 是 | 是 | 是 | 是 |

核心指标：

- success rate
- average steps
- average wall time
- token/cost estimate
- replan count
- test pass rate
- skill hit rate
- skill negative transfer rate
- memory useful hit rate
- repeated-run consistency
- failure taxonomy distribution

成功信号：

- full 相比 baseline success rate 有稳定提升。
- full 的平均步骤或成本没有明显恶化。
- skill/memory 的 useful hit 多于 negative transfer。
- multi-agent trace 能解释失败在哪个角色/节点发生。

失败信号：

- full 成功率无提升但成本显著上升。
- skill 经常误导 DeveloperAgent。
- memory 检索到过期经验导致错误补丁。
- multi-agent 只是增加对话轮次，没有带来更清晰定位或验证。
- replan 高频但不改善最终结果。

### Phase 7：展示与面试材料

目标：把项目讲成“能力机制 + 实验证据”。

交付：

- README：项目定位、架构图、快速运行、A/B 结果。
- `docs/design.md`：Planner、MultiAgent、Skill、Memory 设计。
- `docs/evaluation-contract.md`：实验假设、任务集、指标、失败信号。
- `docs/research-notes.md`：论文启发与取舍。
- `reports/ablation-summary.md`：结果表、失败案例、典型 trace。

面试叙事：

1. 旧项目解决 Agent 基础设施：可控、可测、可回放。
2. 新项目解决 Agent 能力机制：规划、协作、技能、记忆。
3. 不是堆框架，而是做 A/B：
   - skill 可能有负迁移，所以我做 validator。
   - memory 可能过期，所以我做 confidence/source/curation。
   - multi-agent 可能变慢，所以我统计成本和失败归因。

---

## 7. 执行侧 AI 约束

给 Cursor Composer 的执行要求：

- 每个 Phase 单独提交，不要一次性实现所有阶段。
- 先写测试和 fake adapter，再接真实 OpenHands SDK。
- 不要引入 UI。
- 不要下载大数据集。
- 不要把 OpenHands 源码复制进项目。
- 不要把 API key 写入代码或配置文件。
- 每个 public interface 使用类型标注和 docstring。
- 每个 agent 输出结构化对象，禁止只靠自然语言字符串传递核心状态。
- 每个实验结果必须落盘到 `traces/` 或 `reports/`。
- 若 OpenHands SDK API 不稳定，先保持 adapter 层最小可用。

---

## 8. 可直接复制给 Cursor Composer 的第一条提示

```text
请从零实现 RepoSkillAgent 项目的 Phase 0 和 Phase 1。

项目目标：基于 OpenHands Software Agent SDK 构建一个面向小规模 repo 任务的 Agent 能力项目，后续会加入 TaskGraphPlanner、Role-based Multi-Agent、Skill Library 和 Memory System。当前只做工程骨架与 single-agent baseline，不要实现完整多 Agent。

请严格遵守：
1. 不要复刻旧 coding-harness 的完整 harness/eval/policy 细节。
2. 不要做 UI、Docker 平台、分布式 worker 或完整 SWE-bench。
3. OpenHands SDK 必须包在 adapter 层；上层代码不能直接散落依赖 SDK API。
4. 先提供 fake adapter 和单元测试，保证没有 API key 也能跑 pytest。
5. 输出目录结构、核心类型、CLI、trace JSONL、3 个 tiny repo task 的 baseline runner。
6. 所有 agent/runner 输出都要结构化，方便后续 A/B 评测。

请参考根目录的 `PROJECT-PLAN-OpenHands-RepoSkillAgent.zh-CN.md`，只实现 Phase 0 和 Phase 1。
```

---

## 9. 后续增强方向

- 引入 Mem0 作为 memory backend，但保留本地 JSONL/SQLite fallback。
- 参考 MARS 做 budget-aware planner，控制 replan 与子任务搜索成本。
- 参考 SWE-Skills-Bench 增加 skill mismatch/negative transfer 专门评测。
- 参考 Agent Workflow Memory 自动从成功 trace 生成 procedural memory。
- 引入一个轻量 LLM-as-judge 只做 trace 质量审查，不直接替代单元测试和 task assertions。

