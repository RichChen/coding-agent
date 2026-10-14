# HP-03 输出配额与预算计数证据说明

## 固定配额（代码常量）

| 名称 | 值 | 计量口径 |
|---|---|---|
| `MEMORY_PER_STREAM_BYTES` | 65536 (64 KiB) | 每路 stdout/stderr **内存预览**保留上限 |
| `ARTIFACT_PER_TOOL_BYTES` | 1048576 (1 MiB) | 单工具落盘 artifact 上限（每路独立文件） |
| `RUN_OUTPUT_TOTAL_BYTES` | 16777216 (16 MiB) | 单 run `RunOutputMeter.bytes_kept` 总量；触达后 `cancelled_producer` |

证据由 `tests/test_execution_limits.py::test_large_stdout_stderr_respect_memory_and_artifact_caps` 断言：
- `bytes_seen >= 20 MiB`
- `bytes_kept_memory <= 64 KiB`（stdout 与 stderr 各自）
- `bytes_kept_artifact <= 1 MiB`
- `peak_buffer_bytes` / `read_chunks` 有记录（非仅最终字符串长度）

低 run 配额：`test_low_run_quota_cancels_producer` 断言 `cancelled_producer` 或 `run_output_limit`。

## 预算计数

`tests/test_model_budget.py` + `tests/test_cancellation.py::test_model_call_budget_blocks_next_request`：
- `max_model_calls=1` 后共享 ledger 的第二次 AgentLoop：`llm._call_count` 不增加
- `settle_unknown` 后 `tokens_committed` 不回落到“已知零成本”
