# HP-03 支持矩阵（修补后）

| 能力 | 已实现 | Windows 已实测 | Linux 已实测 | 明确不支持 / 待验证 |
|---|---|---|---|---|
| await_with_control 包围模型/工具 | ✓ | ✓（sleep LLM、sleep_only 工具、deadline 0.04） | — | — |
| AgentLoop + loopback 流停滞取消 | ✓ | ✓（`test_agentloop_cancel_during_stream_stall_no_writes`） | — | — |
| 每 attempt 预算预留/结算 | ✓ | ✓（429 不发第二请求） | — | — |
| 缺 usage 拆分费用保守保留 | ✓ | ✓ | — | — |
| cleanup finally + task.cancel | ✓ | ✓ | — | — |
| cleanup_failed 阻断后续写/模型 | ✓ | ✓ | — | — |
| 共享 1MiB artifact（两路合计） | ✓ | ✓ | — | — |
| AgentLoop artifact 安全路径 | ✓ | ✓（接线） | — | — |
| 最小 env + shell 绝对解释器路径 | ✓ | ✓ | — | 原 PATHEXT 根因结论已撤回，见接手验收；不继承全环境 |
| Linux process group 清理 | ✓ | skip | **待验证** | 组外逃逸 |
| Windows controlled 创建前拒绝 | ✓ | ✓ | — | Job Object |
| Docker / SQLite / resume | — | — | — | **本包排除** |
