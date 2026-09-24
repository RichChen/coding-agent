# HP-02 包证据（分片聚合 + eval 生命周期修补）

日期：2026-09-19。任务包：真实增量模型网关与 client 生命周期。

## 基线与约束

- HEAD：`1f5903b620895ad8af3289ffeae529c15c3576a0`（工作区含 HP-01/HP-02 未提交改动）
- 保留用户修改：`docs/changes/SOLID-D2-REMAINING-CLOSEOUT.zh-CN.md`（未覆盖）
- 未改 coding-agent；未提交/推送；**付费 provider 调用数 = 0**
- **不开始 HP-03**（无进程树 / deadline / SQLite / Docker / 恢复功能改动）

## 本轮修补（两缺陷）

1. **工具 ID/名称分片未正确聚合**（`src/llm/stream.py`）
   - 根因：`acc.id` / `acc.name` 按帧覆盖，导致 `"call_"`+`"123"` → `"123"`、`"write_"`+`"file"` → `"file"`。
   - 修复：与 `arguments` 相同，按 index 对 `id`/`name` 做增量字符串拼接（`id_parts` / `name_parts`）。
   - 测试：parser 复现用例 + 两个 AgentLoop 交错用例（TrackingTool 断言 call_id；真实 write/read 工具断言 call_id 与副作用）。

2. **批量评测 owned HTTP client 未关闭**（`src/eval/runner.py`）
   - 根因：`_run_task` 在 `agent.run` 后无生命周期清理；`scripts/run_single.py` 已有 `finally: aclose`。
   - 修复：`_run_task` 包 `try/finally` → `_release_agent_llm`；`LLMClient.aclose` 仍尊重 `owns_http_client`（borrowed/shared 不关底层 httpx）。
   - 子 agent 共享父 llm，自身不调用 `aclose`；仅父任务 `finally` 在结束后释放。
   - 测试：MockTransport 离线断言 `http.is_closed`（成功 / 异常 / 取消 / borrowed 不误关 / subagent 不提前 aclose）。

## 保留的既有修复

- 取消专项：task.cancel + agen.aclose + 有界 fixture cleanup
- `trust_env`：生产默认 True；loopback 测试 False
- 流式专项与完整回归此前已绿；本轮在其上追加用例

## 实际修改文件（本轮）

- `src/llm/stream.py` — id/name 分片拼接
- `src/eval/runner.py` — `_run_task` finally 生命周期接入（不改 grader）
- `tests/test_llm_streaming.py` — 分片聚合 + 双 AgentLoop 交错用例
- `tests/test_eval_llm_lifecycle.py` — eval client 关闭状态离线回归（新建）
- `docs/upgrade/evidence/HP-02/*` — 本报告与原始日志

## 验收命令（实际执行）

解释器：`D:\crq\src\coding-harness\.venv\Scripts\python.exe`

```powershell
Set-Location D:\crq\src\coding-harness
$env:PATH='D:\crq\base\Anaconda3;D:\crq\base\Anaconda3\Scripts;' + $env:PATH
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONDONTWRITEBYTECODE='1'
$env:HTTP_PROXY=''; $env:HTTPS_PROXY=''; $env:ALL_PROXY=''
$env:http_proxy=''; $env:https_proxy=''; $env:all_proxy=''
$env:NO_PROXY='127.0.0.1,localhost'; $env:no_proxy='127.0.0.1,localhost'
$root = 'D:\crq\src\coding-harness\tmp\pytest-hp02-20260919-134957'

# 1) 针对性（分片 + eval 生命周期）
& '.\.venv\Scripts\python.exe' -m pytest `
  tests/test_llm_streaming.py::TestSSEAggregator::test_interleaved_id_name_arguments_fragments_concat `
  tests/test_llm_streaming.py::TestLoopbackStreaming::test_interleaved_id_name_arg_fragments_execute_once_each `
  tests/test_llm_streaming.py::TestLoopbackStreaming::test_interleaved_id_name_arg_fragments_file_tools_call_ids `
  tests/test_eval_llm_lifecycle.py `
  -q --tb=short --basetemp "$root\targeted"
# 8 passed in 3.74s ; targeted_exit=0

# 2) 完整流式专项（代理已清）
& '.\.venv\Scripts\python.exe' -m pytest tests/test_llm_streaming.py -q --tb=short --basetemp "$root\streaming"
# 24 passed in 25.32s ; streaming_exit=0

# 3) 完整回归
& '.\.venv\Scripts\python.exe' -m pytest tests -q -p no:cacheprovider --tb=line --basetemp "$root\full"
# 195 passed in 33.85s ; full_exit=0

# 4) 流式专项 + 保留宿主代理（验证 trust_env=False）
$env:HTTP_PROXY='http://127.0.0.1:9'; $env:HTTPS_PROXY='http://127.0.0.1:9'
$env:http_proxy='http://127.0.0.1:9'; $env:https_proxy='http://127.0.0.1:9'
Remove-Item Env:NO_PROXY -ErrorAction SilentlyContinue
Remove-Item Env:no_proxy -ErrorAction SilentlyContinue
& '.\.venv\Scripts\python.exe' -m pytest tests/test_llm_streaming.py -q --tb=short --basetemp "$root\streaming-with-proxy"
# 24 passed in 24.91s ; streaming_proxy_exit=0
```

原始输出：`pytest-targeted.txt`、`pytest-streaming.txt`、`pytest-streaming-with-proxy.txt`、`pytest-full.txt`、`interpreter.txt`、`proxy-and-basetemp.txt`。

## 结果口径

| 套件 | 本轮可复现结果 | 说明 |
|---|---|---|
| 针对性（分片+lifecycle） | **8 passed, exit 0** | 含 3 个分片相关 + 5 个 eval 生命周期 |
| `tests/test_llm_streaming.py` | **24 passed, exit 0** | 先前 21 + 本轮 3 |
| 同上（保留宿主代理） | **24 passed, exit 0** | `trust_env=False` 避开死代理 |
| `tests` 全量 | **195 passed, exit 0** | 先前 187 + 本轮 8 |

所有进程正常退出；无跳过失败用例。

## 未覆盖

- 真实付费 provider 集成
- HP-03 / HP-04 / Docker / SQLite / 恢复
- `.pytest_tmp` 本机 ACL 损坏（继续用 `tmp/pytest-hp02-*`）

## 风险

- Provider 若对 id/name 发「全量替换」而非分片，拼接仍正确（单帧即完整串）；若同一字段重复发送完整值则会错误拼接——当前按 OpenAI-compatible 增量分片语义实现。
- Eval 路径对每个任务 factory 新建 agent；若外部注入同一 owned client 到多任务，首任务 finally 会关闭它——工厂应按任务创建独立 owned client，或显式 borrowed。
