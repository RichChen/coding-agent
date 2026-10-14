# P1-2 Context L0/L1 增强记录

## 状态

已完成 P1-2 最小可交付：在现有 `micro_compact` 基础上补齐上下文统计与 compact 事件 trace。

本阶段只做 L0/L1：

- L0：保留现有上下文窗口控制入口与配置边界。
- L1：历史 tool result 微压缩，并记录可审计统计。

未做 L2 LLM 总结，避免引入额外 API 调用、语义漂移和重构风险。

## 改动范围

### `src/runtime/compact.py`

新增 `ContextStats`：

- `message_count_before`
- `message_count_after`
- `chars_before`
- `chars_after`
- `chars_saved`
- `tool_messages_before`
- `tool_messages_after`
- `compacted_tool_count`
- `preserved_tool_count`
- `keep_recent`
- `did_compact`

新增 `micro_compact_openai_messages_with_stats()`：

- 保持原地压缩语义。
- 返回 `(messages, ContextStats)`。
- 保留 `read_file` 等 preserve tools 的完整内容。

保留原 `micro_compact_openai_messages()`：

- 函数签名与返回值不变。
- 继续返回压缩后的 messages。
- 内部复用带 stats 的实现，兼容旧调用和旧测试。

`MicroCompactHooks.before_llm()` 现在会把统计写入：

```python
ctx.extra["context_stats"]
```

### `src/runtime/loop.py`

`AgentRunResult` 新增：

```python
context_events: list[dict]
```

当 hook 产生 `context_stats` 且 `did_compact == True` 时：

- 追加到 `result.context_events`。
- 如果启用 `EventBus`，发出 `context_compacted` 事件。

事件 payload 包含：

- `task_id`
- `step`
- 上述 ContextStats 字段

这样可以回答面试追问：

> 长上下文任务中，压缩发生在哪一步？压缩了多少 tool result？节省了多少字符？

### `src/eval/runner.py`

`TraceRun.metadata` 新增：

```python
"context_events": result.context_events
```

因此 eval 产出的 JSONL trace 最后一行 `run_summary.metadata` 可以看到 compact 统计。

### `tests/test_compact.py`

新增覆盖：

- stats 能统计压缩数量、保留数量和节省字符数。
- `MicroCompactHooks` 会写入 `ctx.extra["context_stats"]`。
- `AgentLoop` 会发出 `context_compacted` 事件。
- `AgentRunResult.context_events` 会带回 compact 事件。

## 非目标

本阶段明确不做：

- L2 LLM summary。
- 语义级摘要合并。
- prompt 注入上下文预算说明。
- token-level 精确统计。
- 自动根据上下文长度触发复杂策略。
- 跨 run 的 context 记忆。

## 验证结果

使用用户创建的 conda 环境：

```bash
C:\Users\Administrator\.conda\envs\coding-harness\python.exe -m pytest tests\test_compact.py -q --basetemp .pytest_tmp
```

结果：

```text
12 passed
```

全量测试：

```bash
C:\Users\Administrator\.conda\envs\coding-harness\python.exe -m pytest tests -q --basetemp .pytest_tmp
```

结果：

```text
88 passed
```

## 回退方式

如需回退本阶段：

1. 从 `src/runtime/compact.py` 移除：
   - `ContextStats`
   - `_message_chars`
   - `micro_compact_openai_messages_with_stats`
   - `MicroCompactHooks.before_llm()` 写入 `ctx.extra["context_stats"]` 的逻辑
2. 恢复 `micro_compact_openai_messages()` 为单函数实现。
3. 从 `src/runtime/loop.py` 移除：
   - `AgentRunResult.context_events`
   - run 内 `context_events` 列表
   - `context_compacted` 事件发射逻辑
4. 从 `src/eval/runner.py` 的 `TraceRun.metadata` 移除 `context_events`。
5. 从 `tests/test_compact.py` 删除 P1-2 新增的 stats/event 测试。

## 下一步建议

下一步按总方案进入 P1-3：Agent-as-Tool 最小版。

建议继续保持边界：

- `max_depth=1`
- 子 Agent 只读
- 子 Agent 独立 trace
- 父 trace 只记录子 trace 链接

## 2026-06-25 收尾补强

本次补强没有重做 P1-2，而是在最小版基础上补齐可审计边界：

- 新增 `src/runtime/context.py`，作为 L0/L1 context policy 的统一入口。
- `src/harness/factory.py` 改为通过 `ContextPolicyConfig` / `build_context_hooks()` 装配 context hooks。
- L0 明确对应现有 `ToolContext` 输出限制：`tool_output_max_chars`、`read_file_max_lines`。
- L1 继续使用 `MicroCompactHooks`，未引入 L2 LLM summary。
- compact 新增安全保留规则：
  - 原始 user 任务和 plan 文本属于非 tool 消息，默认不压缩。
  - 最近 1 条失败 tool result 不压缩。
  - 最近若干条 `write_file` / `search_replace` / `edit_file` 相关 tool result 不压缩，用于保留已修改文件线索。
- 新增 `configs/context_compact.yaml`，用于 compact on/off 对比。
- `tests/test_compact.py` 新增 context policy 和关键保留规则测试。

### compact on/off 对比说明

本次未发起联网 API eval，避免把网络/API 波动混入 context 策略判断。

当前可展示证据为 mock/单元测试：

- compact 后字符数下降。
- 原始任务、最近失败、最近修改文件相关结果仍保留。
- `context_compacted` 事件与 `context_events` metadata 可审计。

如需真实对比，可运行：

```bash
python scripts/run_eval.py --dataset datasets/mini_tasks.json --config configs/baseline.yaml --compare --runs 1
python scripts/run_eval.py --dataset datasets/mini_tasks.json --config configs/context_compact.yaml --runs 1
```
