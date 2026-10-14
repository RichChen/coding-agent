# HP-01 包证据

日期：2026-09-19。任务包：严格工具参数与执行入口治理。

## 基线

- HEAD：`1f5903b620895ad8af3289ffeae529c15c3576a0`
- 保留用户未提交修改：`docs/changes/SOLID-D2-REMAINING-CLOSEOUT.zh-CN.md`（未覆盖）
- 参考路径 `learn-Codex-main` 仍不可用；本包不依赖该参考

## 专用环境

- 解释器：`D:\crq\src\coding-harness\.venv\Scripts\python.exe`
- Python 3.13.9（项目 venv，未改共享 Anaconda 站点包）
- 新增运行依赖：`jsonschema>=4.23,<5`（已写入 `pyproject.toml`）
- 完整 freeze：见同目录 `requirements-freeze.txt`、`interpreter.txt`

## 实际修改文件

| 文件 | 作用 |
|---|---|
| `pyproject.toml` | 增加 jsonschema 依赖 |
| `.gitignore` | 忽略 `.venv/` |
| `src/llm/client.py` | 非流式严格解析；非法 JSON 不再变 `{}` |
| `src/tools/validation.py` | **新增** 参数解析/schema/enabled/批量校验入口 |
| `src/tools/base.py` | ToolStatus、SideEffectClass、ToolContext.call_id、status 映射 |
| `src/tools/registry.py` | 未改逻辑（enabled 执行过滤在 validation/loop） |
| `src/runtime/loop.py` | 统一整批校验后再派发；宿主 ID 不注入参数 |
| `src/tools/files.py` 等工具 | side_effect 声明、`additionalProperties: false`、使用 ctx.call_id |
| `src/config/schema.py` | `tools.max_argument_bytes`（默认 65536） |
| `src/harness/factory.py` | 传递 max_argument_bytes |
| `tests/test_tool_validation.py` | **新增** 行为验收测试 |

## 行为反例（旧失败 / 新通过）

旧基线 P1：`invalid_json_arguments= {}`

新结果：

```text
invalid_json_arguments= None
parse_error_kind= invalid_json
```

## 测试命令与结果

解释器：`.venv\Scripts\python.exe`。模型调用数：0。

```powershell
Set-Location D:\crq\src\coding-harness
$env:PATH='D:\crq\base\Anaconda3;D:\crq\base\Anaconda3\Scripts;' + $env:PATH
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONDONTWRITEBYTECODE='1'
& '.\.venv\Scripts\python.exe' -m pytest tests/test_tool_validation.py -q --tb=short
# 19 passed

& '.\.venv\Scripts\python.exe' -m pytest tests -q -p no:cacheprovider --tb=short
# 167 passed（含原先因缺 pytest-asyncio 而 skip 的异步用例）
```

退出码均为 0。平台：Windows 10 / Python 3.13.9。详见 `pytest-tool-validation.txt`、`pytest-full.txt`。

## 有意收紧 / 迁移说明

1. 模型参数中的 `_call_id` 被拒绝（`reserved_field`）；宿主 call_id 仅在 `ToolContext`。
2. 工具 schema 增加 `additionalProperties: false`；未知字段会 schema 拒绝。
3. `run_command` 的 command/argv 互斥在派发前校验（`tool_constraint`）。
4. 同响应任一条校验失败 → 整批不执行（`batch_blocked` + offending id）。
5. 未声明 side_effect 的写工具默认 `non_idempotent`；`run_command` 明确为非幂等。
6. `ToolResult.status` 新增；legacy `success` 保留并与 status 对齐。缺 usage 仍填 0（属 HP-02/契约 C5，本包未改）。

## 未覆盖项

- 真实 SSE / 流式聚合（HP-02）
- 在途取消、进程树、输出边读边限（HP-03）
- 事件存储与恢复（HP-04）
- 真实 provider 集成；Docker/Linux
- Windows 上 `run_command` 非零退出仅用 argv+python 探针验证，未覆盖全部 shell 方言

## 风险

- 旧配置若依赖模型侧注入额外未声明字段，会被 schema 拒绝（有意收紧）。
- 直接调用 `tool.execute` 且只传 `_call_id` 的遗留单测仍可用 fallback；生产路径应走统一派发。
- 本机 Anaconda 解释器仍缺 pytest-asyncio；完整异步验收以项目 `.venv` 为准。
