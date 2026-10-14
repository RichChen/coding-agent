# HP-04：接手实现与离线验收

日期：2026-09-19。基线 HEAD：`1f5903b620895ad8af3289ffeae529c15c3576a0`（承接未提交的 HP-01/02/03 工作，没有回退）。实现者现为 Codex；用户已授权直接接手后续包，不再交 Cursor prompt。本报告的 R1 判断是当日阶段性判断，后续 H3/H5 证据和 [R1 收口记录](../../R1-CLOSEOUT.zh-CN.md) 已更新总体结论。

## 已交付

- `src/tracing/store.py`：每 run SQLite 事务日志、FULL synchronous、跨进程 OS 排他写锁、事件 ID 幂等/冲突检查、seq/内容 hash 校验、只读打开、受控 JSONL 导出与坏尾/坏中段分类。
- `src/tracing/artifacts.py`：内容寻址、原子 publish、大小/hash/run/path 核验；孤儿及 staging 占配额，发布在 DB 引用提交之前；命令启动前预留收集/发布空间。
- `src/runtime/recovery.py`：纯 reducer；消息、操作、累计预算、opaque plugin state、last_seq、终态重建；代码/config/schema/backend/workspace/expiry 校验；文件替换只读核对。
- `src/runtime/session.py`：create/resume/replay API、单进程重入拒绝、真实 runtime 指纹绑定、非幂等 unknown 不重放、模型不确定请求保留预算、原始输出先持久化、终态返回旧结果。
- `src/runtime/loop.py`、`retry.py`：主循环接线；每次模型 attempt 预留/结果都提交；完整 response 保存稳定 operation IDs；intent 先于执行，raw result 先于 masking；结果已提交时恢复复用，不重做工具。
- `src/tools/files.py`：`write_file` 原子替换、写前 before-hash 检查、保留已有权限位；UTF-8 字节写入保证 after-hash 一致。
- `scripts/run_single.py`：`--session-dir` / `--resume` / `--replay`。replay 在配置加载前返回，不创建 client 或执行工具。
- 新增 `tests/test_event_store.py`、`tests/test_recovery.py`、`tests/fixtures/recovery_worker.py`。使用说明见 [SESSION-USAGE](../../SESSION-USAGE.zh-CN.md)。

HP-03 补救改动及验收发现另见 [接手验收记录](../HP-03/CODEX-ACCEPTANCE-20260919.md)；不把 Cursor 接手前的原报告直接当验收依据。

## 行为证据

`recovery_worker` 在真实子进程里调用 `os._exit(71)`；没有异常捕获/正常 close 来伪造崩溃。四个窗口各跑 append、atomic replace 两种 fixture，共八种跨进程恢复：

| 窗口 | append 的效果/恢复 | atomic replace 的效果/恢复 |
|---|---|---|
| response 已存，intent 前 | 原来执行 0 次，恢复首次执行 1 次，最终 `x` | 恢复首次执行 1 次，最终 `new` |
| intent 后、效果前 | 0 次，unknown，不追加 | 0 次，unknown，保持 `old` |
| 效果后、result 前 | 1 次，unknown，保持单个 `x` | 1 次，hash 核对成功，保持 `new` |
| result 后、checkpoint 更新前 | 1 次，复用结果 | 1 次，复用结果 |

各 case 检查调用标记、内容、operation/attempt/result 关系、历史模型调用数；终态再次调用执行器为零。replay 与在线终态/预算一致，opaque plugin state 与过期 checkpoint 的重建状态一致。

其他反例：两个进程争锁只允许一个 writer；DB 损坏/缺失不重建；event ID 异内容拒绝；JSONL 坏尾返回 partial、中段坏行拒绝；未知 major/未注册字段/嵌套到诊断扩展的 oracle 结构拒绝；代码/config/backend/workspace/schema 不匹配、工作区 inode 被替换、artifact 缺失拒绝；绝对 expiry 包含停机时间；中断请求的 calls/tokens/cost 预留仍在；masking 只改消息视图，20KB 原始观察仍可读；命令观察截断后完整有界 stdout 仍可由 artifact 读取，缺引用对象则 replay 失败。

这些测试全部使用 fake model 或本地 Python 子进程，真实 provider/付费模型调用 **0**。

## 验证命令

解释器：`D:\crq\src\coding-harness\.venv\Scripts\python.exe`，Python **3.13.9**；平台 Windows。

```powershell
$env:PATH='D:\crq\base\Anaconda3;D:\crq\base\Anaconda3\Scripts;' + $env:PATH
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONDONTWRITEBYTECODE='1'
$env:HTTP_PROXY=$null; $env:HTTPS_PROXY=$null; $env:ALL_PROXY=$null
$env:NO_PROXY='127.0.0.1,localhost'
& '.\.venv\Scripts\python.exe' -m pytest tests -q -p no:cacheprovider --tb=short --basetemp=tmp/accept-hp04-release
```

阶段结果：初版 store/recovery **16 passed**；含 HP-03 和旧 oracle/runner 的回归选集 **64 passed**；补充恢复/取消选集 **24 passed**；上次全量 **252 passed / 6 skipped，exit 0，53.98s**。`scripts/run_single.py --help` 与无 config 的 replay 子进程均 exit 0；`git diff --check` exit 0（仅已有 CRLF 提示）。最终代码全量结果在下方收尾记录。

### 最终代码收尾记录

上述 `tmp/accept-hp04-release` 命令实际返回 **exit 0**：

```text
253 passed, 6 skipped in 54.24s
```

最后增加的“artifact 额度不足时命令进程不得创建”、JSONL 导出不得覆盖数据库、minor 诊断扩展不能嵌套对象检查已包含在此轮。六个 skip 全部来自 `tests/test_linux_cleanup.py` 的真实 Linux 平台条件，没有关闭异步测试或用 skip 掩盖 Windows 失败。

**当日验收结论：HP-04 上述本地支持范围通过；HP-03 的 Linux 清理验收及 H3 强隔离仍未通过/未执行。** 这段保留为当日状态，不覆盖后续 H3/H5 验收。

## 支持与限制

此包是单机本地恢复实现，不是分布式锁或外部 exactly-once。支持 react、no-op/masking；planner、自定义可执行 hook、subagent 的持久恢复明确拒绝。write_file 之外的未确认写入一律保守 unknown。损坏日志不自动修复；旧 trace 不转为可信恢复历史。

checkpoint 当前仅作为派生缓存写入，启动始终从 SQLite 事件重建。日志 schema 及 minor 白名单仅经本仓 fixture 验证，不代表候选 v0.2 已发布或跨仓确认。存储包含原始观察，属于 workspace 外的宿主私有数据；当前本地后端未提供抵抗恶意 shell 的宿主文件隔离。

**截至本报告日期，HP-03 的 Linux 进程树实测仍未完成；HP-04 的本地事务/恢复可以独立验收。** 六项 skip 均为 Linux shell/argv × 三种清理场景。本机未发现 Docker CLI，既有 WSL 探针未得到可用 Linux 环境；没有安装、没有远程连接。后续 H3 需要明确可用的 Linux/Docker 执行环境并另行细化后端/独立 grader 任务包；该后续已在 H3 证据中完成。

参考工程路径仍不存在。用户原有 `docs/changes/SOLID-D2-REMAINING-CLOSEOUT.zh-CN.md` 保持原样；未改对方仓库、未提交/推送。
