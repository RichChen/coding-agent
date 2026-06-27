# P1-3 只读 Agent-as-Tool 记录

## 状态

已完成 P1-3 最小可交付：父 Agent 可以通过 `subagent_task` 工具委托一个只读子 Agent 完成聚焦分析任务。

本阶段严格保持边界：

- `max_depth=1`
- 子 Agent 只读
- 子 Agent 独立 trace
- 父 Agent 通过 tool result 链接子 trace
- 不做多 worker、递归、多 Agent 协商或冲突合并

## 参考项目情况

AGENTS.md 指定的参考项目路径：

```text
C:\Users\23500\Desktop\src\learn-Codex-main
```

当前执行环境中不可访问，`Test-Path` 返回 `False`。本阶段实现因此基于当前项目已有的 `AgentLoop`、`Tool`、`TraceLogger` 和配置装配模式完成。

## 改动范围

### `src/tools/subagent.py`

新增 `SubagentTaskTool`：

- 工具名：`subagent_task`
- 参数：`task`
- 内部启动一个子 `AgentLoop`
- 子 Agent 仅注册：
  - `read_file`
  - `list_dir`
- 子 Agent 使用只读 system prompt
- 子 Agent 固定 `max_depth=1`
- 子 Agent 不注册 `subagent_task`，避免递归委托

工具返回 JSON：

```json
{
  "trace_file": "...",
  "summary": "...",
  "files_inspected": ["..."],
  "findings": ["..."],
  "suggested_next_steps": [],
  "confidence": "medium",
  "success": true,
  "failure_reason": "none"
}
```

### `src/runtime/loop.py`

`ToolContext.extra` 现在会在父 Agent 执行工具时携带当前 `event_bus`。

这让 `subagent_task` 在父 EventBus 启用时可以发出：

```text
subagent_completed
```

### `src/config/schema.py`

新增：

```python
RuntimeSubagentsConfig
```

配置字段：

- `enabled`
- `max_depth`
- `readonly`
- `max_steps`

挂载到：

```yaml
runtime:
  subagents:
```

### `src/harness/factory.py`

当：

```yaml
runtime:
  subagents:
    enabled: true
```

且：

```yaml
tools:
  enabled:
    - subagent_task
```

时注册 `SubagentTaskTool`。

如果启用了 subagents 但没有把 `subagent_task` 放入 `tools.enabled`，会抛出清晰错误，避免配置静默失效。

### `configs/subagent_readonly.yaml`

新增只读 Agent-as-Tool 示例配置：

- 启用 `runtime.subagents`
- 启用 `subagent_task`
- 开启 lifecycle events
- 保持 hardened 类似的 sandbox/command policy

### `tests/test_subagent.py`

新增覆盖：

- `SubagentTaskTool` 能启动只读子 Agent 并写独立 trace。
- 父 Agent 能调用 `subagent_task`，并在 tool result 中拿到子 trace 链接。
- 父 EventBus 能记录 `subagent_completed`。
- `configs/subagent_readonly.yaml` 能通过 `load_config()` 和 `build_agent()` 装配出 `subagent_task`。

## 非目标

本阶段没有做：

- 子 Agent 写文件
- 多层递归
- 多 worker 并发
- 父子 Agent 协商
- 子 Agent 结果自动合并到文件
- 独立模型或独立 provider 配置
- 子 Agent 专用 eval 数据集

这些应放到后续更高优先级确认后再做。

## 验证结果

新增测试：

```bash
C:\Users\Administrator\.conda\envs\coding-harness\python.exe -m pytest tests\test_subagent.py -q --basetemp .pytest_tmp
```

结果：

```text
3 passed
```

全量测试：

```bash
C:\Users\Administrator\.conda\envs\coding-harness\python.exe -m pytest tests -q --basetemp .pytest_tmp
```

结果：

```text
91 passed
```

## 回退方式

如需回退本阶段：

1. 删除 `src/tools/subagent.py`。
2. 删除 `configs/subagent_readonly.yaml`。
3. 删除 `tests/test_subagent.py`。
4. 从 `src/config/schema.py` 移除：
   - `RuntimeSubagentsConfig`
   - `RuntimeConfig.subagents`
5. 从 `src/harness/factory.py` 移除 `SubagentTaskTool` 注册逻辑。
6. 从 `src/runtime/loop.py` 的 `ToolContext(...)` 移除 `extra={"event_bus": self.event_bus}`。

## 下一步建议

按总方案，P1 阶段最小能力闭环已完成：

- P1-1 Planner
- P1-2 Context L0/L1
- P1-3 只读 Agent-as-Tool

下一步建议进入 P2-1：LLMClient provider adapter / streaming event 雏形。

如果面试时间更近，也可以先做一个小型真实 demo：

```bash
python scripts/run_single.py "Ask a subagent to inspect README and summarize risks" --config configs/subagent_readonly.yaml
```

## 2026-06-25 收尾补强

本次补强没有重做 P1-3，而是在最小版基础上补齐可展示证据与父子 trace 链接：

- `SubagentTaskTool` 输出新增 `child_task_id`。
- 从子 Agent `final_answer` 轻量解析：
  - `summary`
  - `findings`
  - `suggested_next_steps`
  - `confidence`
- 父 `AgentRunResult` 新增 `subagent_traces`。
- 父 Agent 调用 `subagent_task` 成功后，会从 tool result JSON 提取：

```json
{"child_task_id": "...", "trace_file": "...", "success": true}
```

- `src/eval/runner.py` 和 `scripts/run_single.py` 会把 `subagent_traces` 写入父 run summary metadata。
- `datasets/repo_tasks.json` 新增 `medium_subagent_cross_file` 任务，引导父 Agent 先用 `subagent_task` 分析跨文件问题再修复。
- 新增 fixture：`tests/fixtures/repos/medium_subagent_cross_file/`。
- 新增展示材料：`docs/examples/subagent_trace_redacted.jsonl`。
- `tests/test_subagent.py` 新增父 trace metadata 与结构化输出测试。

### demo/eval 说明

本次未发起联网 API demo。原因是 P1-3 收尾目标主要是代码与 trace 能力闭环，mock 测试已覆盖父子 Agent 调用、子 trace 链接、父 metadata 写入。

如需真实展示，可运行：

```bash
python scripts/run_single.py --config configs/subagent_readonly.yaml "Use subagent_task to inspect parser.py and service.py, then explain the fix."
```
