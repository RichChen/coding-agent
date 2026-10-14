# HP-03 修补证据（在途 await / 每 attempt 预算 / 清理 / 终止门控）

> 历史实现报告。2026-09-19 接手验收又发现取消清理、shell 探针和 Linux fixture 覆盖缺口；当前结论以 [Codex 接手验收](CODEX-ACCEPTANCE-20260919.md) 为准。下文 PATHEXT 根因和测试通过数不作为当前代码验收证据。HP-04 现已由 Codex 接手实现。

日期：2026-09-19。平台：Windows 10。**不宣布 HP-03 全验收**（Linux 进程树仍待实测）。

## 约束

- 参考项目路径仍不存在；未伪称已读
- 保留 `docs/changes/SOLID-D2-REMAINING-CLOSEOUT.zh-CN.md`
- 未改 coding-agent；未提交/推送；付费调用 = 0；未进 HP-04

## 本轮修补对照审查缺陷

### 1. 真正包围在途 await
| 项 | 代码 | 测试 | 本机结果 |
|---|---|---|---|
| `await_with_control` 竞态 work/cancel/deadline，取消后有界等待 | `src/runtime/awaitctl.py` | `test_await_with_control_deadline`；`test_run_deadline_interrupts_model_await_not_success`（deadline=0.04 vs sleep 0.25 → **success=False**, RUN_DEADLINE, elapsed&lt;0.2s） | **通过** |
| 模型开始后 cancel | 同上 + RetryPolicy | `test_cancel_during_model_await_not_success` | **通过** |
| 不轮询的慢工具 | loop 包 `tool.execute` | `test_host_interrupts_sleep_only_tool_no_polling`（写工具 calls=0） | **通过** |
| Loopback 流停滞取消 | AgentLoop + SSE gate | `test_agentloop_cancel_during_stream_stall_no_writes`（首帧后 cancel，write 次数=0） | **通过** |
| 子 agent | `subagent.py` 共享 cancel/deadline | 既有 subagent 测试 + 共享 wiring | **通过**（无独立子账本） |

撤回：旧报告「在途 HTTP 取消已测」若仅指 client 层 cancel 测试——现已补 **AgentLoop+loopback 流停滞** 用例。

### 2. 每 attempt 预留/结算
| 项 | 代码 | 测试 | 结果 |
|---|---|---|---|
| reserve 在 RetryPolicy 每次循环内 | `src/runtime/retry.py` | `test_retry_reserves_each_attempt_max_calls`：max_model_calls=1，429 后 **HTTP 次数=1**，`calls_started=1` | **通过** |
| 失败 attempt → unknown，保留预留 | `model_budget.settle_unknown` | 同上 + `test_unknown_usage_keeps_reserve` | **通过** |
| 仅 total、无 prompt/completion 拆分 → 费用不归零 | `settle` cost_provenance=`conservative_reserve` | `test_cost_without_split_keeps_conservative_reserve` | **通过** |
| 输入估算 | `estimate_input_tokens` = `chars_div_4_json` | 经 retry 记录 `estimate_method` | **实现** |
| 非法价格 | `__post_init__` 校验 | `test_invalid_price_rejected` | **通过** |

### 3. 清理在 cancel/异常路径
| 项 | 代码 | 测试 | 结果 |
|---|---|---|---|
| `execute` finally 回收；task.cancel 返回 CANCELLED | `src/execution/local.py` | `test_backend_task_cancel_still_reclaims` | **通过** |
| 有界 collector wait；关 pipe transport（减 Proactor 警告） | finally 关 `_transport` | 全量回归无 warnings summary | **改善** |
| Linux 组级 TERM/KILL + leader 退出后仍验组 | `_cleanup_process` / `_verify_group_gone` | Linux 用例 skip | **待 Linux** |
| legacy 不宣称树回收 | `capabilities.tree_reclaim_guaranteed` | 文档 | **明确** |

### 4. 终止阻止后续副作用
| 项 | 代码 | 测试 | 结果 |
|---|---|---|---|
| cleanup_failed → 停后续写与下一模型请求 | loop `batch_stop_kind` | `test_cleanup_failed_blocks_subsequent_write_and_model`（writer.calls=0, llm calls=1） | **通过** |
| 跳过原因保持真实 termination_kind（非一律 user_cancelled） | `_skip_remaining(kind=...)` | 同上 CLEANUP_FAILED | **通过** |
| ToolResult 带 exit_code/cleanup_*/truncated/bytes_* | `command.py` / `base.py` | execution_limits 映射用例 | **通过** |

### 5. 输出配额
| 项 | 代码 | 测试 | 结果 |
|---|---|---|---|
| stdout+stderr **共享** 1MiB artifact | `ToolArtifactBudget` | 大输出用例断言两路合计 ≤1MiB 且核对文件大小 | **通过** |
| 每路内存 64KiB；run 16MiB | 常量 + meter | 既有大输出 / 低 run 额度 | **通过** |
| AgentLoop 接线 artifact 到 `.harness_artifacts/<task>/<safe_op>/` | loop extra | 路径不信任原始 call_id | **实现** |

### 6. `test_shell_path_still_works`
根因：空 allowlist 完整替换 env 时缺少 **`PATHEXT`**，cmd 无法将 `python` 解析为 `python.exe`。  
修复：`build_minimal_env` Windows 最小键加入 `PATHEXT`（仍不继承 HOME/USERPROFILE）。  
单独与全量均通过；**不是**恢复全环境继承。

## 验收命令与结果

basetemp：`tmp/pytest-hp03-20260919-150628`（及 patch targeted）。

| 套件 | 结果 |
|---|---|
| cancel/limits/budget/command | 见 `pytest-patch-targeted.txt`（35 passed, 1 skipped） |
| HP-01+HP-02+subagent | **48 passed** |
| 全量（含新 stream stall） | **223 passed, 1 skipped**, exit 0（`pytest-full.txt`） |

## 未完成（不得宣称全验收）

- Linux marker / ignore-TERM / leader 先退 / shell+argv：**测试已写，本机 skip**
- Windows Job Object / Docker：明确不做
- Process group 外逃逸：不保证

## 支持矩阵

见 `SUPPORT-MATRIX.md`（已按本轮实测更新）。
