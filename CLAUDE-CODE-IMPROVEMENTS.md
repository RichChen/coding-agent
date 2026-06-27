# coding-harness 改进任务书（对照 learn-claude-code-main）

> **用途**：把本文档交给 Claude Code，在 `coding-harness` 仓库内按优先级实现。  
> **参考仓库**：`c:\Users\23500\Desktop\src\learn-claude-code-main`（教学型 Harness，12 课渐进脚本 + Web）  
> **目标仓库**：`c:\Users\23500\Desktop\src\coding-harness`（评测导向的 Agent + Eval Harness）

---

## 0. 背景与原则

### 0.1 两个项目的定位差异

| 维度 | learn-claude-code-main | coding-harness（当前） |
|------|------------------------|-------------------------|
| 目标 | 教「Harness 心智模型」 | 可复现实验 + baseline/hardened A/B |
| 结构 | 12 个独立 `agents/sNN_*.py` | 模块化 `src/{runtime,policy,tools,eval,tracing}` |
| 安全 | 分散在工具内（`safe_path`、bash 黑名单） | 独立 `policy/`（沙箱、CommandPolicy、Budget） |
| 评测 | 无正式 eval 管线 | `EvalRunner` + `mini_tasks.json` + 报告 |
| 观测 | s12 `EventBus`、s06 `.transcripts/` | `TraceLogger` JSONL（仅 `run_single` 默认开启） |

### 0.2 借鉴原则（必须遵守）

1. **保持 coding-harness 的模块边界**：不要把 12 课脚本合并成一个巨型文件；借鉴的是**机制**，不是目录结构。  
2. **保持 OpenAI 兼容消息格式**：learn 项目用 Anthropic `tool_use` / `tool_result`；本仓库用 `assistant.tool_calls` + `role: tool`，适配层只在 `llm/client.py`。  
3. **评测优先**：任何改动应让 `pytest tests/ -v` 通过，且 `run_eval` 的指标更可解释。  
4. **不要引入 Web / 多 Agent 团队 / Skills 课程全套**（见 §6 明确不做）。  
5. **小步提交**：按 §4 的 P0 → P1 → P2 分 PR 或分 commit，每阶段可独立 review。

### 0.3 learn 项目里「已经更好、不必照搬」的部分

- 独立 `policy/`、`CommandPolicy` 白名单、`EvalRunner` 三种 `expected.type` — **保留并加强**。  
- `Tool` ABC + `ToolRegistry` — 比 `TOOL_HANDLERS` dict 更适合单测；可选增加 dispatch 表，**不必删掉 ABC**。  
- `RetryPolicy`、YAML 双配置 — learn 项目没有等价物。

---

## 1. 对照结论：值得借鉴的设计（按价值排序）

| # | 借鉴点 | learn 出处 | 解决 harness 的什么问题 |
|---|--------|------------|-------------------------|
| A | **工具输出截断 + read 行数限制** | `s02` `run_read` limit、`[:50000]` | 长文件/长命令撑爆 context，eval 成本高 |
| B | **落实 `file_size_limit_bytes`** | YAML 已有、代码未读 | hardened 配置「假安全」 |
| C | **Loop 前置 Hook（可插拔）** | `s_full.py` 每轮 LLM 前 `microcompact` | 在不改主循环结构下加压缩/提醒 |
| D | **Layer 1 微压缩（micro_compact）** | `s06_context_compact.py` | 多轮 tool 后 messages 膨胀 |
| E | **指标与运行时计数对齐** | —（harness 自身债） | `tool_failure_rate`、`policy_block`、`step_number` |
| F | **统一 agent 装配 + eval 接 trace** | —（harness 自身债） | `build_agent` 重复、批量评测无 JSONL |
| G | **EventBus 式生命周期事件** | `s12` `EventBus` | trace 只有 step，缺 task/worktree 级事件 |
| H | **共享 `build_agent` + 配置校验** | learn 无，但 harness 需要 | scripts 重复、pydantic 未用 |
| I | **Mock LLM 集成测试** | learn 仅 `test_s_full_background` mock | CI 无 API Key 无法测 `AgentLoop` |
| J | **edit_file 式替换 vs search_replace** | `s02` `run_edit` replace once | 模型常因「非唯一匹配」失败（可选新工具） |

---

## 2. P0 — 必须先做（正确性 / 配置诚信 / 指标）

### P0-1：实现 `policy.file_size_limit_bytes`

**参考**：`configs/hardened.yaml` 第 58 行；learn 的 `run_read` 有隐式体量控制思路。

**改动**：

1. 在 `Sandbox` 或新建 `src/policy/limits.py` 增加 `check_file_size(path: Path, limit: int) -> Optional[str]`。  
2. `ReadFileTool` / `WriteFileTool` 执行前检查；超限返回 `ToolResult(success=False, error=...)`。  
3. `build_agent`（见 P1-1）从 `policy_cfg` 传入 limit；`baseline`/`hardened` 已有不同值。  
4. 测试：`tests/test_tools.py` 增加超限读/写用例。

**验收**：

- `file_size_limit_bytes: 100` 时读大文件失败且 agent 可继续（tool 错误消息）。  
- `pytest tests/test_tools.py -v` 通过。

---

### P0-2：修正评测指标与运行时语义

**参考**：`LEARNING.zh-CN.md` §4 答案；`src/eval/metrics.py` 69–71 行。

**改动**：

1. `AgentRunResult` 增加 `total_tool_invocations: int`；`loop.py` 每执行一次 `tool.execute`（含 unknown tool）+1。  
2. `tool_failure_rate = sum(tool_failures) / sum(total_tool_invocations)`，分母为 0 时返回 0。  
3. `aggregate_metrics` 的 `policy_block_count` 改为 `sum(r.policy_blocks for r in results)`（或同时保留 `failure_reason` 列但文档说明差异）。  
4. `AgentState`：在每次完成一轮 tool 循环后 `step_number += 1`；`StepRecord.step` 使用真实序号。  
5. 更新 `tests/test_runner.py` 中 metrics 相关断言。

**验收**：

- 一轮 3 个 tool、2 次失败 → `total_tool_invocations=3`，`tool_failure_rate≈66.7%`。  
- `policy_blocks>0` 的任务在报告 `policy_block_count` 中体现，即使 `failure_reason` 仍为 `none`。

---

### P0-3：工具输出体量护栏（不依赖 LLM）

**参考**：`learn-claude-code-main/agents/s02_tool_use.py` 第 61–68、43–58 行。

**改动**：

1. `configs/*.yaml` 的 `policy` 下增加（带默认值）：
   ```yaml
   tool_output_max_chars: 50000
   read_file_max_lines: null   # 或 500
   ```
2. `ReadFileTool`：可选 `limit` 参数；超长时截断并附 `... (N more lines)`。  
3. `RunCommandTool`：合并 stdout/stderr 后截断到 `tool_output_max_chars`。  
4. `read_file` 仍受 `file_size_limit_bytes` 约束（先检查文件大小再读）。

**验收**：

- 10 万字符命令输出被截断，且 `success` 语义不变（可按 returncode）。  
- 现有 `test_tools` 不回归。

---

## 3. P1 — 架构增强（向「能跑长任务的生产 Harness」靠拢）

### P1-1：抽取 `src/harness/factory.py`（或 `src/config/loader.py`）

**问题**：`scripts/run_single.py` 与 `scripts/run_eval.py` 各有一份 `load_config` + `build_agent`。

**改动**：

1. 新建模块，导出：
   - `load_config(path: Path) -> dict`（含 `${VAR:default}` 解析）  
   - `build_agent(config: dict, workspace: Path, *, tracer: TraceLogger | None = None) -> AgentLoop`  
2. 两个 script 改为 `from src.harness.factory import ...`（包名可微调，但勿再用顶层 `coding_harness` 除非同步改 `pyproject`）。  
3. **禁止**在 factory 里写业务逻辑，只做装配。

**验收**：

- `run_single` / `run_eval` 行为与改前一致（手动 smoke 即可）。  
- 无重复 `build_agent` 代码块。

---

### P1-2：Loop 前置 Hook 管线

**参考**：`learn-claude-code-main/agents/s_full.py` 约 725 行（`microcompact(messages)` 在 `messages.create` 之前）。

**设计**：

```python
# src/runtime/hooks.py
class LoopHooks:
    async def before_llm(self, messages: list, ctx: HookContext) -> list: ...
    async def after_tools(self, messages: list, ctx: HookContext) -> list: ...
```

**改动**：

1. `AgentLoop.__init__(..., hooks: LoopHooks | None = None)`。  
2. 在 `loop.py` 中 `llm.chat` **之前**调用 `hooks.before_llm`；工具全部执行完、append tool messages **之后**可选 `after_tools`。  
3. 默认 `hooks=None` 时行为与现在完全一致。

**验收**：

- 无 hooks 时 `pytest` 全绿。  
- 注册 no-op hook 不改变 messages。

---

### P1-3：Context micro-compact（Layer 1 only）

**参考**：`learn-claude-code-main/agents/s06_context_compact.py` 的 `micro_compact`、`KEEP_RECENT=3`、`PRESERVE_RESULT_TOOLS={"read_file"}`。

**改动**：

1. 新建 `src/runtime/compact.py`，实现 `micro_compact_openai_messages(messages, *, keep_recent=3, preserve_tools={"read_file"})`。  
   - 适配 OpenAI 格式：`role: tool` 消息，根据 `tool_call_id` 回溯 assistant 里 `function.name`。  
   - 仅压缩「超过 100 字符」的旧 tool content 为 `[Previous: used {name}]`。  
2. 实现 `MicroCompactHooks(LoopHooks)` 在 `before_llm` 调用。  
3. `configs/*.yaml` 增加：
   ```yaml
   runtime:
     context:
       micro_compact: false
       keep_recent_tool_results: 3
   ```
4. hardened 可默认 `false`，提供 `configs/long_run.yaml` 示例开启。

**验收**：

- 单元测试：构造 5 条 tool 消息，压缩后最近 3 条保留原文，`read_file` 的旧结果不被清。  
- 开启 micro_compact 后 `messages` 总字符数下降（断言即可）。

**注意**：Layer 2 `auto_compact`（LLM 总结替换全历史）**放在 P2**，P1 不要做（避免 eval 不可复现）。

---

### P1-4：`run_eval` 默认写 trace + 与 task_id 关联

**参考**：learn `s12` `EventBus` 的 JSONL 思路；harness 已有 `TraceLogger`。

**改动**：

1. `run_eval.py` 的 `agent_factory` 为每个 task 创建 `TraceLogger(output_dir=config["tracing"]["output_dir"])`。  
2. `log_run` 的 metadata 含 `config_name`、`task_id`、`expected_check`（评测结束后补写或二次 log）。  
3. 报告 CSV 增加列 `trace_file`（相对路径），便于从失败任务跳到 JSONL。

**验收**：

- `python scripts/run_eval.py --config configs/hardened.yaml --dataset datasets/mini_tasks.json` 后 `traces/` 有与任务数相当的文件。  
- 不改变 `aggregate_metrics` 的 passed 定义。

---

### P1-5：用 Pydantic 校验 YAML 配置（轻量）

**参考**：`pyproject.toml` 已依赖 pydantic；learn 用 YAML frontmatter 但无 agent 配置 schema。

**改动**：

1. `src/config/schema.py`：`HarnessConfig` 嵌套 `LLMConfig`、`RuntimeConfig`、`PolicyConfig`、`ToolsConfig`、`TracingConfig`。  
2. `load_config` 返回 `HarnessConfig` 或 `model_validate` 后的 dict。  
3. 未知字段：`model_config = ConfigDict(extra="forbid")` 或 `ignore`（团队选一，文档写明）。  
4. `file_size_limit_bytes` 必须在 schema 中存在。

**验收**：

- 故意写错 YAML key 时启动失败并提示字段名。  
- 现有 `baseline.yaml` / `hardened.yaml` 能通过校验。

---

## 4. P2 — 可选增强（时间允许再做）

### P2-1：Lifecycle EventBus（扩展 tracing）

**参考**：`learn-claude-code-main/agents/s12_worktree_task_isolation.py` 第 82–100 行。

**改动**：

1. `src/tracing/events.py`：`EventBus.emit(event, **payload)` 追加 JSONL 到 `{output_dir}/events.jsonl`。  
2. 在 `AgentLoop` 发射：`run_start`、`llm_complete`、`tools_complete`、`run_end`、`budget_exhausted`。  
3. 可选工具 `read_events`（仅 debug 配置启用）— **不要**默认加入 hardened 工具列表。

---

### P2-2：`edit_file` 工具（单次 replace）

**参考**：`s02` `run_edit` — `content.replace(old_text, new_text, 1)`。

**改动**：

1. `src/tools/edit.py`：`EditFileTool`，行为与 learn 一致，走 `Sandbox.resolve`。  
2. 与现有 `search_replace`（必须唯一）并存；`enabled` 列表由 YAML 控制。  
3. 测试：无匹配 / 单次替换成功。

---

### P2-3：Mock LLM 的 `AgentLoop` 集成测试

**参考**：`learn-claude-code-main/tests/test_s_full_background.py` mock 模式。

**改动**：

1. `tests/fixtures/mock_llm.py`：固定两轮响应（先 `tool_calls` read_file，再纯文本答案）。  
2. `tests/test_agent_loop.py`：临时 workspace + mock LLM，断言 `messages` 长度、`success`、`steps` 条数。  
3. CI 不依赖 `LLM_API_KEY`。

---

### P2-4：Layer 2 auto-compact（显式开关，默认关）

**参考**：`s06` `auto_compact` + `.transcripts/` 落盘。

**仅当** P1-3 稳定后实现；**eval 默认必须关闭**，否则不同 run 不可对比。  
需：压缩前写 `traces/transcripts/{task_id}_{ts}.jsonl`；用**独立** summarizer 调用（可配置 cheap model）。

---

## 5. 实现时 code pointers（方便 Claude Code 定位）

### learn-claude-code-main

| 文件 | 借鉴内容 |
|------|----------|
| `agents/s02_tool_use.py` | `TOOL_HANDLERS` 分派、输出截断、`safe_path` |
| `agents/s06_context_compact.py` | `micro_compact` / `estimate_tokens` / transcript 备份 |
| `agents/s_full.py` | 每轮 LLM 前 hook 链顺序 |
| `agents/s12_worktree_task_isolation.py` | `EventBus.emit` JSONL 模式 |
| `agents/s03_todo_write.py` | Todo nag（**本次不做**，仅 future） |

### coding-harness（主要修改面）

| 文件 | 预期改动 |
|------|----------|
| `src/runtime/loop.py` | hooks、tool 计数、step_number |
| `src/runtime/hooks.py` | 新建 |
| `src/runtime/compact.py` | 新建 micro_compact |
| `src/tools/files.py` | limit、size check |
| `src/tools/command.py` | 输出截断 |
| `src/eval/metrics.py` | 精确 tool_failure_rate |
| `src/eval/runner.py` | trace 路径回写 |
| `scripts/run_single.py` / `run_eval.py` | 改用 factory |
| `src/harness/factory.py` 或 `src/config/*` | 新建 |
| `configs/*.yaml` | 新字段 |
| `tests/*` | 覆盖 P0/P1 |

---

## 6. 明确不做（避免 scope creep）

以下在 learn 项目里有，但**本任务书不要求实现**：

- Next.js `web/` 学习站、`extract-content.ts`  
- s04–s11 多 Agent、MessageBus、plan approval、autonomous idle  
- s12 Git worktree 并行（除非用户另开任务；与 eval 临时 workspace 模型不同）  
- s05 Skills / `load_skill` 动态加载  
- 切换到 Anthropic SDK 或改 `stop_reason` 驱动循环（保持现有 `has_tool_calls` 语义）  
- Docker / nsjail（README 已列为远期）  
- SWE-bench 全量对接  

---

## 7. 建议执行顺序（给 Claude Code）

```
P0-1 file_size_limit
  → P0-3 output truncation
  → P0-2 metrics + step_number + tool invocations
  → P1-1 factory
  → P1-2 hooks
  → P1-3 micro_compact
  → P1-4 eval traces
  → P1-5 pydantic config
  → P2-* 按需
```

每完成一个 P0/P1 子项：

1. 运行 `pytest tests/ -v`  
2. 若改动配置，同步 `README.zh-CN.md` 配置说明（简短一段即可）  
3. 若改动指标，同步 `LEARNING.zh-CN.md` §4 参考答案中相关数字/公式  

---

## 8. 完成定义（Definition of Done）

- [ ] 所有 P0 子项已实现并有测试  
- [ ] P1-1～P1-4 至少完成（P1-5 强烈建议）  
- [ ] `pytest tests/ -v` 全绿  
- [ ] `configs/hardened.yaml` 中声明的安全/限制项均有代码对应  
- [ ] `run_eval` 产出 trace 文件且报告可关联 `task_id`  
- [ ] 未破坏 baseline vs hardened 对比实验的语义（`passed = success ∧ expected_check` 不变）  

---

## 9. 给 Claude Code 的起始提示（可直接复制）

```
请阅读仓库根目录 CLAUDE-CODE-IMPROVEMENTS.md，从 P0 开始按顺序实现。
参考 learn-claude-code-main 的路径见文档 §5，但不要复制其 Anthropic API 格式。
保持 OpenAI 兼容 messages/tool 消息链。
每完成一个子项运行 pytest tests/ -v，通过后再做下一项。
不要实现文档 §6 中「明确不做」的内容。
```

---

*文档生成依据：对 `learn-claude-code-main` 与 `coding-harness` 的架构对比及现有 `LEARNING.zh-CN.md` 已知局限。*
