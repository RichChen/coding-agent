# P2-1 LLMClient Adapter / Streaming 雏形记录

## 状态

已完成 P2-1 最小可交付：在保持现有非流式 `LLMClient.chat()` 兼容的前提下，补 provider adapter 结构、错误分类和 streaming event 合约雏形。

## 改动范围

### `src/llm/client.py`

新增：

- `LLMErrorKind`
- `LLMStreamEvent`
- `BaseLLMClient`
- `OpenAICompatibleAdapter`
- `LLMClient.stream_chat()`

现有 `LLMClient.chat()` 保持主路径不变，仍返回 `LLMResponse`。

### Provider adapter

`OpenAICompatibleAdapter` 负责：

- chat completions URL
- payload 构造
- headers 构造

这样后续接入其他 OpenAI-compatible provider 时，不需要把 provider 差异散落在 runtime 中。

### Streaming event skeleton

`stream_chat()` 当前不是完整 SSE 实现，而是在现有非流式 `chat()` 上输出稳定事件合约：

- `message_delta`
- `tool_call_delta`
- `llm_stream_done`
- `llm_error`

**Runtime 接入（2026-06-25 polish）**：`tracing.llm_stream_events: true` 时，`AgentLoop._call_llm()` 走 `stream_chat()` 并将上述事件写入 `EventBus`（见 `configs/debug.yaml`）。eval 配置默认仍为 `false`。

后续如果实现真实 SSE，可以保留这个事件 contract，不影响 UI/trace 层。

### 错误分类

`LLMError` 新增 `kind`：

- `timeout`
- `http`
- `parse`
- `unknown`

## 非目标

本次没有做：

- 真正 SSE 增量解析
- cancel token
- 多 provider 完整适配
- token/cost 计费
- UI streaming

这些可以作为后续 P2 扩展。

## 验证

新增：

- `tests/test_llm_client.py`

覆盖：

- adapter payload/headers
- parse error 分类
- tool call parsing
- stream event skeleton
- stream error event

Focused 测试：

```bash
C:\Users\Administrator\.conda\envs\coding-harness\python.exe -m pytest tests/test_llm_client.py -q --basetemp .pytest_tmp
```

结果：

```text
5 passed
```

全量测试：

```bash
C:\Users\Administrator\.conda\envs\coding-harness\python.exe -m pytest tests -q --basetemp .pytest_tmp
```

结果：

```text
107 passed
```

## 回退方式

如需回退：

1. 从 `src/llm/client.py` 移除：
   - `LLMErrorKind`
   - `LLMStreamEvent`
   - `BaseLLMClient`
   - `OpenAICompatibleAdapter`
   - `stream_chat()`
2. 恢复 `LLMError` 为普通异常。
3. 恢复 `LLMClient.chat()` 内联 payload/url/header 构造。
4. 删除 `tests/test_llm_client.py`。
