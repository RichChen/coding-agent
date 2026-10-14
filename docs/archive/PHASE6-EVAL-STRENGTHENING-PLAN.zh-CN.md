# Phase 6 Evaluation Strengthening Plan

> 用途：交给 Cursor Composer 执行。  
> 目标：把当前 Phase 6 从“评测管线跑通”补强到“可以支撑 Agent 能力机制有效性的证据”。

---

## 0. 当前诊断

现有 Phase 6 已完成：

- 24 个 tiny repo tasks。
- A0-A5 ablation matrix。
- repeats / seed / variance。
- memory isolation。
- JSON + Markdown report。
- pytest 和 ruff 均通过。

但当前结果无法证明机制收益：

- A0 baseline 已经 `success_rate=1.00`，且 `avg_steps=2`。
- A1-A5 也都是 `success_rate=1.00`，但 `avg_steps=5`。
- memory 有 retrieval/useful 计数，但没有带来 success/steps/replan 改善。
- 24 个任务本质是 3 个基础任务各 8 个 wording 变体。
- FakeAdapter 会用 task id 前缀匹配 scripted fixes，因此 `fix_import_error_caseXX` 等任务都会被硬编码补丁解决。

补强目标不是让所有指标变好，而是让评测能诚实地区分：

- baseline 能解决什么；
- planner/multi-agent/skill/memory 分别改变了什么；
- 哪些机制有收益，哪些只是增加成本；
- 哪些负结果也值得报告。

---

## 1. 最终验收标准

补强后至少满足：

- A0 baseline 不再 100% 饱和，建议 success rate 在 `0.50-0.85`。
- A1/A2/A3/A4/A5 至少有一个机制在某类任务上产生可解释变化：
  - success rate 提升；
  - steps 降低；
  - failure taxonomy 变好；
  - skill negative transfer 被识别；
  - memory 在 repeated/holdout 任务上降低定位或修复成本。
- reports 中不再出现 `卤`，使用 ASCII `+/-` 或正确 UTF-8 `±`。
- 默认 repeats 调到 3，和 `docs/evaluation-contract.md` 保持一致。
- ablation report 明确标注任务类型、机制开关、结果限制。

---

## 2. Phase 6.1：修报告与配置一致性

### 任务

1. 修改 `reposkill_agent/eval/report.py`：
   - 把 `卤` 替换成 `+/-`，避免 Windows 终端/Markdown 编码问题。
   - 表格列名改为：
     - `success_rate+/-std`
     - `avg_steps+/-std`
     - `avg_replan+/-std`

2. 修改 `scripts/run_phase6_ablation.py`：
   - 默认 `--repeats` 改为 `3`。
   - 输出命令行参数到 summary，包括：
     - tasks path
     - repeats
     - seed
     - seed_memory
     - adapter

3. 修改 `docs/evaluation-contract.md`：
   - 记录“当前 toy eval 的限制”。
   - 明确区分：
     - plumbing validation
     - mechanism evidence
     - final project evidence

### 验收

```bash
python -m pytest -o cache_dir=.tmp/pytest_cache --basetemp=.tmp/pytest
python -m ruff check reposkill_agent tests scripts benchmarks
python scripts/run_phase6_ablation.py --tasks benchmarks/tasks/phase6_tiny_24.yaml --repeats 3 --seed 42
```

报告中不能出现 `卤`。

---

## 3. Phase 6.2：新增 non-scripted / hard tasks

### 背景

当前 `SCRIPTED_FIXES` 只有 3 个基础修复，但 `FakeAdapter.apply_scripted_fix()` 会对 `task_id.startswith(f"{key}_")` 做前缀匹配，导致 24 个 case 都能被硬编码补丁解决。

这对 pipeline 测试有用，但不适合证明能力机制。

### 任务

新增一个任务文件：

```text
benchmarks/tasks/phase6_hard_12.yaml
```

新增 12 个任务，要求：

- 不使用 `fix_import_error_*`、`fix_off_by_one_*`、`add_greeting_function_*` 这些会命中 scripted fix 的前缀。
- 至少包含 4 类：
  - `rename_symbol`
  - `update_api_signature`
  - `add_regression_test`
  - `parse_pytest_traceback`
- 每类 3 个 case。
- 每个 case 使用独立 tiny repo 目录，或至少不同 task id + repo fixture。

建议新增 repo：

```text
benchmarks/repos/rename_symbol/
benchmarks/repos/update_api_signature/
benchmarks/repos/add_regression_test/
benchmarks/repos/parse_pytest_traceback/
```

### 任务设计要求

每个 repo 必须：

- 初始测试失败。
- 有清晰 expected_files。
- 有 `conftest.py` 保证 import path 稳定。
- 不能被现有 `SCRIPTED_FIXES` 自动修复。

### 验收

运行：

```bash
python scripts/run_phase6_ablation.py --tasks benchmarks/tasks/phase6_hard_12.yaml --repeats 3 --seed 42
```

预期：

- A0 baseline 不应全过。
- failure taxonomy 中应出现 `test_failure` 或 `patch_missing`。

---

## 4. Phase 6.3：引入 A0_unscripted 或关闭前缀补丁

### 方案 A：新增 Adapter 开关

在 `FakeAdapter` 中增加：

```python
allow_prefix_scripted_fixes: bool = True
```

然后：

- pipeline smoke test 保持 `True`。
- Phase 6 hard eval 使用 `False`。

### 方案 B：新增 Ablation Config

新增：

```text
A0_unscripted
```

它使用 fake adapter，但不允许 scripted fixes。

### 推荐

优先做方案 A，因为最小且清晰。

### 验收

- 旧 `phase6_tiny_24.yaml` 仍可作为 plumbing validation。
- 新 `phase6_hard_12.yaml` 能让 baseline 暴露失败。

---

## 5. Phase 6.4：区分 A1 Planner 与 A2 Multi-Agent

### 当前问题

`A1_planner` 和 `A2_multi_agent` 当前都走 `TaskGraphRunner` + role agents，结果完全一样。配置名上有区别，机制上区别不够。

### 任务

增加一个执行模式：

```python
execution_mode: Literal["single_graph", "role_agents"]
```

行为：

- `single_graph`：
  - 使用 task graph；
  - 但节点都由一个 `GraphSingleAgentExecutor` 处理；
  - trace 中 `agent_role="planner_agent"`。
- `role_agents`：
  - 使用现有 `ManagerAgent / LocatorAgent / DeveloperAgent / QAAgent`。

Ablation 映射：

- A1_planner -> `single_graph`
- A2_multi_agent -> `role_agents`

### 验收

- A1/A2 trace 的 `agent_role` 明显不同。
- 报告中能显示：
  - role_handoff_count
  - agent_roles_used

---

## 6. Phase 6.5：让 Skill/Memory 至少影响一个决策点

### 当前限制

Skill 和 Memory 目前主要是 telemetry：

- skill ids 被记录到 `skills_applied`；
- memory hints 被检索和记录；
- 但 DeveloperAgent 仍主要依赖 scripted fixes。

### 最小增强

不要接 LLM，不要做复杂 patch synthesis。只做 deterministic influence：

1. 在 `DeveloperAgent` 中根据 `active_skills` 和 `memory_hints` 选择 patch strategy。
2. 为 hard tasks 增加 skill-driven deterministic patch：
   - `rename_symbol_across_files`
   - `update_api_signature`
   - `inspect_pytest_traceback`
3. 如果没有对应 skill/memory，则返回 `patch_missing` 或保守失败。

### 预期效果

- A0/A1 可能失败。
- A3_skill 对 skill-covered tasks 成功率提升。
- A4_memory 对 repeated/seeded tasks 在第二轮能提升或减少步骤。

### 重要

不要伪造收益。若 skill/memory 只覆盖部分任务，报告要按 task category 分组。

---

## 7. Phase 6.6：分组报告

### 新增指标

在 `AblationRunner` 或 `report.py` 中按 task tags 分组：

- import
- logic
- feature
- rename
- api
- regression
- traceback
- repeated

每组输出：

- success_rate
- avg_steps
- avg_replan_count
- failure taxonomy

### Markdown 报告新增章节

```markdown
## By Task Category

| Config | Category | Tasks | Success Rate | Avg Steps | Main Failure |
```

### 目的

避免整体 success rate 掩盖某类任务的机制收益。

---

## 8. Phase 6.7：最终运行矩阵

保留两个任务集：

### 8.1 Plumbing Eval

```bash
python scripts/run_phase6_ablation.py --tasks benchmarks/tasks/phase6_tiny_24.yaml --repeats 3 --seed 42
```

用途：

- 验证评测管线稳定。
- 预期所有配置大多成功。
- 不用于证明机制收益。

### 8.2 Hard Mechanism Eval

```bash
python scripts/run_phase6_ablation.py --tasks benchmarks/tasks/phase6_hard_12.yaml --repeats 3 --seed 42
```

用途：

- 证明机制差异。
- 重点看 A0/A1/A2/A3/A4/A5 的增量。

### 8.3 Seeded Memory Eval

```bash
python scripts/run_phase6_ablation.py --tasks benchmarks/tasks/phase6_hard_12.yaml --repeats 3 --seed 42 --seed-memory
```

用途：

- 检查 memory 是否能在 repeated pattern 中产生收益。

---

## 9. 最终 README 叙事

最终项目不要写：

> Full agent beats baseline on all tasks.

应该写：

> I built a reproducible ablation framework for repo-task agents. The initial toy benchmark showed baseline saturation, so I introduced harder non-scripted tasks and separated plumbing validation from mechanism evidence. On hard tasks, the evaluation reports which mechanisms improve success/steps and where skill or memory creates negative transfer.

中文面试叙事：

> 我没有只报一个 demo pass rate。Phase 6 一开始发现 baseline 已经 100% 饱和，于是我把评测分成 plumbing eval 和 hard mechanism eval。前者验证系统稳定，后者验证机制差异。这能说明我知道怎么避免“看起来都过了但其实没有证明收益”的 Agent 评测陷阱。

---

## 10. 给 Composer 的第一条提示

```text
请执行 `PHASE6-EVAL-STRENGTHENING-PLAN.zh-CN.md`。

目标：补强 Phase 6 评测，使其不只是 pipeline validation，而是能支撑 Agent 机制收益判断。

请按顺序做：
1. 修 `reposkill_agent/eval/report.py` 中的 `卤`，改成 `+/-`。
2. 默认 repeats 改成 3，并更新 `docs/evaluation-contract.md`。
3. 新增 `benchmarks/tasks/phase6_hard_12.yaml` 和对应 4 类 hard tiny repos。
4. 为 FakeAdapter 增加关闭 prefix scripted fix 的开关，并让 hard eval 使用关闭模式。
5. 区分 A1 planner-only 与 A2 role-agent execution。
6. 让 skill/memory 至少影响 deterministic patch strategy，不要只记录 telemetry。
7. 报告增加 task category 分组。
8. 跑 plumbing eval、hard mechanism eval、seeded memory eval，并写出报告。

约束：
- 不接 LLM。
- 不下载外部数据。
- 不做 UI。
- 不破坏现有 tiny_24 plumbing eval。
- 每一步都要保持 pytest 和 ruff 通过。
```

