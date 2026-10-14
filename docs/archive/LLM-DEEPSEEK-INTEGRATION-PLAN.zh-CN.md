# LLM / DeepSeek Integration Plan

> 用途：交给 Cursor Composer 执行。  
> 目标：在现有 deterministic RepoSkillAgent 机制骨架上，接入真实模型 `deepseekv4pro`，形成可运行的 LLM Agent eval。  
> 运行环境：conda env `coding-agent`。  
> 安全要求：不要把 API key 写入仓库、配置文件、测试文件、trace、report 或 README。

---

## 0. 重要安全约束

用户会在本地 shell 中通过环境变量提供 API key。

不要在任何文件中写入真实 key。

禁止出现：

```text
sk-...
```

推荐 PowerShell 本地运行方式：

```powershell
conda activate coding-agent
$env:LLM_PROVIDER = "deepseek"
$env:LLM_MODEL = "deepseekv4pro"
$env:LLM_BASE_URL = "<DeepSeek/OpenAI-compatible base url, verify from provider docs>"
$env:LLM_API_KEY = "<set locally, never commit>"
```

如果实际模型名不是 `deepseekv4pro`，以 provider 文档/控制台为准，只改环境变量，不改代码。

---

## 1. 当前状态判断

现有项目已经有：

- deterministic task graph planner；
- role agents；
- skill retrieval / validation；
- memory persistence / retrieval；
- A0-A5 ablation；
- hard deterministic eval；
- optional `OpenHandsAdapter`。

但当前主评测仍然是 fake/deterministic：

- hard task 的成功来自 deterministic patch strategy；
- skill/memory 确实影响 patch strategy，但不是 LLM 推理；
- OpenHands path 只在 baseline 中有 optional hook，没有进入 A0-A5 主评测；
- 还没有 DeepSeek/OpenAI-compatible model client。

本计划要补的不是更多 toy task，而是真实 LLM execution layer。

---

## 2. 目标分层

最终项目应区分三类 eval：

1. **Plumbing Eval**
   - fake adapter；
   - tiny tasks；
   - 证明 runner/trace/report 稳定。

2. **Deterministic Mechanism Eval**
   - fake adapter；
   - hard tasks；
   - 证明 planner/skill/memory 机制链路可解释。

3. **LLM Mechanism Eval**
   - DeepSeek real model；
   - hard tasks；
   - 证明真实模型在 skill/memory/plan 上下文下能更好地产生 patch。

Phase 7 之前必须至少完成第 3 类的 smoke + 小规模 ablation。

---

## 3. 新增模块设计

### 3.1 新增模型客户端

新增目录：

```text
reposkill_agent/llm/
  __init__.py
  client.py
  prompts.py
  schemas.py
```

### 3.2 `client.py`

实现一个 OpenAI-compatible Chat Completions 客户端。

建议依赖：

- 可选：`httpx>=0.27`
- 如果不想加依赖，可用标准库 `urllib.request`，但 `httpx` 更清晰。

接口：

```python
class ModelClient:
    def complete_json(
        self,
        *,
        system: str,
        user: str,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> dict:
        ...
```

环境变量：

```text
LLM_PROVIDER=deepseek
LLM_MODEL=deepseekv4pro
LLM_BASE_URL=<base url>
LLM_API_KEY=<secret>
LLM_TIMEOUT_SECONDS=60
```

要求：

- API key 只能从环境变量读。
- timeout 必须可配置。
- 请求/响应错误要结构化返回。
- trace 中不要写完整 prompt 和 key，只写摘要、token/cost 占位、error type。
- 支持 dry-run / mock client 测试。

---

## 4. LLM Developer Agent

新增：

```text
reposkill_agent/agents/llm_developer.py
```

目标：

让模型根据 task、文件内容、skill、memory、test output 生成 patch。

### 输入上下文

从 `AgentContext` 和 adapter 获取：

- task issue；
- expected_files；
- relevant file contents；
- previous actions；
- active skills；
- memory hints；
- latest test output if available；
- repo file list；
- current failing tests。

### 输出 schema

新增 `reposkill_agent/llm/schemas.py`：

```python
class FileEdit(BaseModel):
    path: str
    content: str
    reason: str

class PatchPlan(BaseModel):
    summary: str
    edits: list[FileEdit]
    confidence: float
    needs_more_context: bool = False
```

LLM 必须输出 JSON。  
若 JSON parse 失败：

- 记录 `llm_parse_error`；
- 不要应用半截补丁；
- 返回失败，让 replan/QA 处理。

### Patch 应用策略

- 先只支持 full file rewrite，即 `PatchSpec(path, content, mode="write")`。
- 每次最多改 `max_files_per_patch=3`。
- 只能修改 task expected_files 或 locator 命中的文件。
- 若 LLM 修改不在允许路径内，拒绝并记录 `patch_rejected_path_scope`。

---

## 5. Graph Runner 接入

在 `TaskGraphRunner` 增加参数：

```python
developer_mode: Literal["deterministic", "llm"] = "deterministic"
```

CLI 增加：

```bash
python -m reposkill_agent run-graph --adapter fake --developer-mode llm
```

注意：

- adapter 仍可用 fake workspace，因为 fake adapter 提供本地读写/pytest。
- LLM 只负责生成 patch，不负责直接执行命令。
- 这样能避免一开始就依赖 OpenHands SDK 的全部 agent runtime。

推荐优先路径：

```text
FakeAdapter workspace/tools + DeepSeek LLMDeveloperAgent
```

而不是先走：

```text
OpenHands full Conversation
```

原因：

- 可控；
- trace 更清晰；
- 方便 A/B；
- 便于对比 deterministic developer vs LLM developer。

---

## 6. LLM Eval Matrix

新增脚本：

```text
scripts/run_llm_ablation.py
```

新增报告目录：

```text
reports/llm/
```

### 6.1 Smoke Eval

先跑 3 个 hard tasks：

```bash
python scripts/run_llm_ablation.py `
  --tasks benchmarks/tasks/phase6_hard_12.yaml `
  --limit 3 `
  --repeats 1 `
  --seed 42
```

目标：

- 验证 API 调用可用；
- 验证 JSON patch parse；
- 验证 patch application；
- 验证 pytest；
- 验证 trace/report。

### 6.2 Small LLM Mechanism Eval

再跑 12 个 hard tasks，repeats 1 起步：

```bash
python scripts/run_llm_ablation.py `
  --tasks benchmarks/tasks/phase6_hard_12.yaml `
  --repeats 1 `
  --seed 42
```

配置：

| Config | Planner | Multi-Agent | Skill | Memory | Developer |
| --- | --- | --- | --- | --- | --- |
| L0_llm_single | no | no | no | no | llm |
| L1_llm_planner | yes | no | no | no | llm |
| L2_llm_multi | yes | yes | no | no | llm |
| L3_llm_skill | yes | yes | yes | no | llm |
| L4_llm_memory | yes | yes | no | yes | llm |
| L5_llm_full | yes | yes | yes | yes | llm |

### 6.3 成本控制

默认：

- repeats=1；
- max tasks=12；
- temperature=0；
- max_tokens=2048；
- 每个 task 最多 2 次 LLM call；
- 失败不无限 retry。

后续稳定后再 repeats=3。

---

## 7. Prompt 设计

### System Prompt

要求模型是代码修复 agent：

- 输出 JSON；
- 不解释长篇自然语言；
- 不编造文件；
- 只改允许文件；
- 优先最小补丁；
- 必须保持测试意图。

### User Prompt 包含

- issue；
- task id；
- expected files；
- file contents；
- failing test output；
- task graph node；
- active skills；
- memory hints；
- constraints。

### Skill 注入

只注入验证通过的 skill：

```text
Skill ID:
Purpose:
Procedure:
Verifier:
Negative transfer notes:
```

### Memory 注入

只注入 compact hint：

```text
Memory type:
Source task:
Outcome:
Workflow:
Confidence:
```

---

## 8. Metrics

LLM eval 新增指标：

- `llm_call_count`
- `llm_parse_error_count`
- `llm_patch_rejected_count`
- `llm_patch_applied_count`
- `llm_prompt_tokens_estimate`
- `llm_completion_tokens_estimate`
- `llm_wall_time_ms`
- `llm_error_type`
- `success_rate`
- `avg_steps`
- `avg_replan_count`
- `skill_negative_transfer_count`
- `memory_useful_count`

注意：

- 如果 provider 返回 token usage，就记录真实值。
- 如果没有 usage，就用字符数粗略估计，并标注 `token_estimate_mode=char_approx`。

---

## 9. 测试要求

新增 tests：

```text
tests/test_llm_client.py
tests/test_llm_developer.py
tests/test_llm_ablation.py
```

必须覆盖：

- mock ModelClient 返回合法 JSON；
- mock ModelClient 返回非法 JSON；
- LLMDeveloperAgent 拒绝越权路径；
- LLMDeveloperAgent 成功应用 full-file edit；
- `run_llm_ablation.py --mock-llm` 可离线跑通；
- 无 `LLM_API_KEY` 时真实 LLM eval 给出清晰错误，不跑到一半才失败。

测试不能调用真实 API。

---

## 10. README / Docs 更新

更新 README：

必须明确三层评测：

```text
1. Fake plumbing eval
2. Deterministic mechanism eval
3. Real LLM mechanism eval
```

新增 DeepSeek 运行说明：

```powershell
conda activate coding-agent
$env:LLM_PROVIDER = "deepseek"
$env:LLM_MODEL = "deepseekv4pro"
$env:LLM_BASE_URL = "<verify from provider docs>"
$env:LLM_API_KEY = "<your key>"
python scripts/run_llm_ablation.py --tasks benchmarks/tasks/phase6_hard_12.yaml --limit 3 --repeats 1
```

不要写真实 key。

更新 `docs/evaluation-contract.md`：

- deterministic eval 不能替代 LLM eval；
- LLM eval 是最终项目证据；
- fake eval 只用于 CI 和机制回归。

---

## 11. 验收命令

基础：

```powershell
conda activate coding-agent
python -m pytest -o cache_dir=.tmp/pytest_cache --basetemp=.tmp/pytest
python -m ruff check reposkill_agent tests scripts benchmarks
```

Mock LLM：

```powershell
python scripts/run_llm_ablation.py --tasks benchmarks/tasks/phase6_hard_12.yaml --limit 3 --mock-llm
```

真实 DeepSeek smoke：

```powershell
python scripts/run_llm_ablation.py --tasks benchmarks/tasks/phase6_hard_12.yaml --limit 3 --repeats 1 --seed 42
```

成功标准：

- mock LLM 必过；
- 真实 LLM 至少能完成 API call、patch parse、pytest loop；
- 即使任务失败，也必须有完整 trace/report；
- 不允许把 API key 写入任何文件。

---

## 12. 给 Composer 的执行提示

```text
请执行 `LLM-DEEPSEEK-INTEGRATION-PLAN.zh-CN.md`。

目标：为 RepoSkillAgent 增加真实 LLM execution layer，使用 DeepSeek/OpenAI-compatible Chat Completions API。用户会在本地 shell 通过环境变量提供 API key，严禁把 key 写入任何文件。

运行环境：conda env `coding-agent`。

请按顺序实现：
1. 新增 `reposkill_agent/llm/`，实现 ModelClient、prompt builder、PatchPlan schema。
2. 新增 `LLMDeveloperAgent`，让模型根据 task/files/skills/memory/test output 生成 full-file edits。
3. 在 `TaskGraphRunner` 增加 `developer_mode=deterministic|llm`。
4. 新增 `scripts/run_llm_ablation.py`，实现 L0-L5 小规模 LLM eval。
5. 新增 mock LLM 测试，真实 API 不进入单元测试。
6. 更新 README 和 evaluation contract，明确 fake eval / deterministic eval / LLM eval 三层边界。
7. 保证 pytest 和 ruff 通过。

不要：
- 不要提交 API key。
- 不要把真实 prompt 全量写进 report。
- 不要直接跳到 OpenHands full runtime；优先使用 FakeAdapter workspace/tools + LLMDeveloperAgent。
- 不要删除已有 deterministic eval。
```

