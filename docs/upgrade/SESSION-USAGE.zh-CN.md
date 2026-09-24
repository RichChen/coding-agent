# HP-04：本地持久会话使用说明

2026-09-19。本仓 opt-in 能力；旧运行方式保持可用。本文记录的是 Windows 本地 SQLite/文件锁、fake model 和临时工作区的会话接口；Docker、跨仓和 R1 总体结论见 [R1 收口记录](R1-CLOSEOUT.zh-CN.md)，不把本地会话文档单独扩大为跨平台保证。

## 入口

现有 `scripts/run_single.py` 新增互斥选项：

- `--session-dir <新目录>`：创建持久会话，目录必须不存在，且位于 agent workspace 之外。
- `--resume <已有目录>`：使用相同 task、config、workspace 恢复；必须显式传 `--workspace`。不得把旧 JSONL 当作恢复数据库。
- `--replay <已有目录>`：只读摘要，不加载配置、不创建模型 client、不执行工具；过期会话仍可 replay。

以下为用户手动运行形式；本轮未执行会调用真实模型的 create/resume 命令：

```powershell
.\.venv\Scripts\python.exe scripts/run_single.py "同一个任务描述" --config configs/baseline.yaml --workspace D:\harness-workspaces\demo --session-dir D:\harness-runs\demo
.\.venv\Scripts\python.exe scripts/run_single.py "同一个任务描述" --config configs/baseline.yaml --workspace D:\harness-workspaces\demo --resume D:\harness-runs\demo
.\.venv\Scripts\python.exe scripts/run_single.py --replay D:\harness-runs\demo
```

真实调用仍需单独的费用授权和配置。CLI 的 help 和无配置 replay 已在离线测试中执行。

Python API：以 `compatibility(workspace=..., code_id=source_fingerprint(repo), config=..., backend=...)` 计算预期指纹；在 `with RunSession.create(...) as session` 或 `with RunSession.resume(..., expected=...) as session` 中调用 `await session.run(agent, task)`。`RunSession.replay(path)` 返回纯重建状态，不接受执行器。API 调用方负责提供真实代码/config/backend 身份；CLI 已自动计算源码（含未提交修改）和配置 hash。

## 恢复规则

SQLite 是事实来源；每个 run 由跨进程 OS 锁独占写入，没有租约过期抢占。进程死亡由 OS 释放锁，同进程并发 run 也会拒绝。数据库不存在、损坏、序列/hash/身份不符时拒绝恢复，不自动新建或回退到 JSONL。

模型 attempt 先预留预算并提交 `model.started`，再请求模型；工具先提交 `tool.intent` 再执行。operation ID 在已保存的 response 内稳定，attempt ID 每次新建。每条事件有 schema、run/task、seq、UTC、进程内累计单调耗时和关联字段。运行总时限另由绝对 UTC expiry 控制，停机占用总时限及当前 step 时限。

| 崩溃点 | 恢复动作 |
|---|---|
| 完整 response 已保存，工具 intent 尚未提交 | 可首次执行该工具；没有已提交 intent 的路径不能先产生该工具副作用 |
| intent 已提交，无 result | 默认 unknown，即使没有 started 事件也不能假设没执行 |
| `write_file` 原子替换后无 result | 仅当 before 与 after 不同且当前文件 hash 等于 after，记录核对成功；不再次写入 |
| append / 自由 shell / edit 等无 result | unknown，不自动重放；停止该批后续工具 |
| result 已提交但 checkpoint 过期 | 从事件重建并复用 result，不再执行 |
| 模型 attempt 已开始但完整 response 未保存 | unknown；保留预留账，不重发不确定请求 |
| run.finished 已提交 | 返回已保存结果，执行器调用为零 |

checkpoint 是可丢弃缓存。当前最小实现始终从事件重建；尚未以 checkpoint 加速启动。纯 reducer 同时重建当前消息视图、操作、累计预算、opaque plugin state、最终结果及 last_seq。`set_plugin_state` 是宿主 API，不是让模型直接写内部状态的工具。

## 支持边界

持久 loop 支持 react、无 hook/no-op hook、现有 `MicroCompactHooks` masking，以及 H4 内置窗口策略（no-op/fixture 插件）。H4 的 `context.prepared` 同时保存发送视图与策略状态，详见 [H4 说明](H4-IMPLEMENTATION.zh-CN.md)。plan_act、自定义可执行 hook/插件、subagent 在会话启动前明确拒绝。已有非持久路径仍可使用原配置。这个限制避免把未实现的 planner/子任务状态恢复伪装为完整恢复。

原始工具结果在 masking 前持久化；大 payload 和命令 stdout/stderr 先原子发布为 artifact，再提交事件引用。恢复验证 run 归属、受控路径、大小、SHA-256。命令 staging 副本仅在引用提交后移除，内容仍由 artifact 保留；崩溃残留和孤儿文件计入配额，不自动删除取证数据。

默认事件 JSON payload 总额 16 MiB，artifact/staging 合计发布检查上限 16 MiB，单 artifact 2 MiB，checkpoint 16 MiB。SQLite 页/索引/事务 journal 有额外磁盘开销，这些数字不是整个数据库目录的物理字节上界。命令流另受 HP-03 的每路 64 KiB 内存、每工具合计 1 MiB artifact、每 run 16 MiB 输出额度约束。超过 journal/artifact 配额会拒绝继续副作用；发布但未提交引用的文件也占额度。

存储应位于宿主管理的私有目录，不能挂入 agent workspace。数据库和 artifact 包含原始任务/观察，不作为公开报告；配置仅存 hash，认证配置不会序列化为明文。当前 trusted_local/legacy_host 没有文件系统隔离，目录分离不能阻止恶意自由 shell 读取宿主文件，强隔离需 H3 容器。模型可见和公开 trace 的进一步脱敏协议仍由后续契约定义。

JSONL 仅导出/审计：同 event ID 同内容幂等，异内容拒绝；坏尾行显式 `partial_tail`，应从 SQLite 重导出；坏中间行拒绝。未知 schema major 和未注册 envelope 字段拒绝，本地 minor 白名单 fixture 不代表对方仓库已接受候选 v0.2。
