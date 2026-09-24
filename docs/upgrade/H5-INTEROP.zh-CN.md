# H5 跨仓 H4 联调报告

2026-09-21，coding-harness 宿主与 `D:\crq\src\coding-agent` 的 RepoSkill H4 adapter 完成一次真实 DeepSeek Flash + Docker 联调。联调使用对方固定的 `h4-handoff-20260921-v2` 交接包，插件源代码按整体 SHA256 固定为：

```text
32c1c40a902c2206d2e524aaf0ea8716421b117dc454a8bc8fa15cb442ab5a5e
```

宿主只注册显式 ID `reposkill`，注册信息绑定 adapter 名称、wire 版本、实现源码摘要、公开 task、公开文件树、空 memory snapshot、能力和 `action_dispatch=disabled`。配置不能写任意 Python import 字符串；未注册外部插件、源码漂移、同步实现、重复 ID 和私有字段都会拒绝。持久 `RunSession` 现在接受内置插件或此类 host-issued wrapper，并把完整注册指纹纳入 runtime fingerprint；配置漂移会在模型调用前拒绝恢复。

## 联调结果

## Dispatcher 接线（当前代码）

当前宿主配置可将 `runtime.context.dispatcher` 设为 `read_search`。`build_agent` 只在 `docker_linux` backend 上构造 `ReadSearchDispatcher`；loop 把同一 run deadline、取消事件、输出 meter 和 session 传给 hook。dispatcher 的固定 RPC 只允许相对公开 workspace 的 `read`/`search`，不接受 shell、写入、绝对路径、父级遍历或隐藏路径。每次调用返回带 operation/attempt、状态、输出 hash、字节/截断和清理状态的 receipt；宿主把受限结果作为不可信 user observation 注入下一次模型视图，并以 `plugin.dispatch` journal 事件持久化。runtime fingerprint 包含 dispatcher 和 backend 能力，恢复时配置漂移会 fail closed。

离线 preflight 已在 `offline-02/` 通过。`real-02/` 只记录了 Docker named pipe 权限导致的 `invalid_env`；full-host 重跑的有效 dispatcher 证据位于 `real-04/`。`real-03/` 的运行本身完成，但旧验证脚本顺序错误，未生成最终摘要。

交接包任务 `public-settings-001` 的私有 grader 固定 4 个探针。基线在付费调用前为 1/4，证明原始 bug 存在。随后以同一个 public seed、private spec、模型、预算、窗口和空 memory 分别运行两次：

| 变体 | 模型 calls | grader | candidates requested / injected | proposals |
| --- | ---: | ---: | ---: | ---: |
| 插件 off | 4 | 4/4 | 0 / 0 | 0 |
| 插件 on | 4 | 4/4 | 2 / 2 | 3，全部 `dispatcher_not_enabled` |

两次都使用 Docker `coding-harness-h3-tests@sha256:18872d...e78e`、network=none、无宿主挂载、无 key。每次 model start 都有前置 `context.prepared` journal 序号；SQLite replay 与 `events.jsonl` 一致，候选快照由宿主独立 grader 重建。模型没有收到 private EvaluationSpec，私有 canary 和当前 key 都未进入模型侧证据。

插件 on 的候选是公开证据定位/记忆上下文，作为不可信 user 消息注入模型视图；它们没有变成 system 指令。RepoSkill adapter 的 action proposals 仍被宿主明确拒绝，没有执行 read/search，也没有伪造 InjectionReceipt。这里的 `prepared_view_injections` 只是 H4 context 记录，不代表模型采纳或工具执行。

用量为 Flash provider 返回值：off 6,811 tokens（输入 6,325、输出 486），on 7,322（输入 6,687、输出 635），合计 14,133 tokens / 8 calls。按当日官方峰时/非峰时区间粗估约 **$0.00119–$0.00239**；cost ledger 的硬上限为每 run $0.03，实际 `cost_usd` 仍为 null，未冒充账户账单。没有摘要或额外插件模型调用，插件是纯本地 async 规则。

## 证据

- [dispatcher full-host 有效联调目录](evidence/H5-interop/real-04/)
- [有效结果摘要](evidence/H5-interop/real-04/summary.json)
- [完整历史联调目录](evidence/H5-interop/real-01/)
- [离线 preflight（off/on、指纹、交接样例一致性）](evidence/H5-interop/real-01/preflight.json)
- [插件开启的模型候选 patch](evidence/H5-interop/real-04/on/candidate.patch)
- [插件关闭的独立评测](evidence/H5-interop/real-04/off/evaluation-result.json)
- [插件开启的独立评测](evidence/H5-interop/real-04/on/evaluation-result.json)

本仓新增 `src/policy/registry.py`、`src/policy/reposkill.py`、`src/policy/dispatcher.py` 和 `scripts/run_reposkill_interop.py`；对方仓库没有写入。注册器只解决可信代码的显式登记和绑定，不能把进程内 Python 变成恶意插件沙箱。H5 dispatcher 只接受 `read`/`search` 声明，固定在已启动的 Docker workspace 内执行，拒绝 shell、写入、绝对路径、父级遍历和隐藏路径；每次执行生成 operation/attempt、输出 hash、清理状态，并写入 `plugin.dispatch` journal 事件。插件 on 的下一轮输入只获得宿主生成的不可信 evidence observation。

## 验证边界

这次仍是单个合成公开任务的 off/on 烟测，不是修复率实验，也不能证明 memory、完整思考模式、Pro 模型或多任务稳定性。`offline-02/` 已验证 dispatcher 配置和交接 fixture 的离线边界；`real-02/` 的 `invalid_env` 不计入结果，`real-04/` 是当前有效的 full-host dispatcher 联调证据。对方仓库当前没有可用 Git 根目录供提交状态比较；本轮通过固定源文件 hash 和交接 artifact hash 约束版本。
