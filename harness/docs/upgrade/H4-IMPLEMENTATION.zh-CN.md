# H4 基础版：窗口视图与策略插件接口

2026-09-20。完成 IMPLEMENTATION-PLAN 中“接口 + none/masking”的首版范围，同时提供明确标记的本地摘要 fixture，以验证四种视图的协议与恢复行为。没有调用真实模型、付费摘要或另一仓库的 RepoSkill。

## H3 复核

H3 没有阻止 H4 的新增问题。本轮全量测试显式启用真实 Docker，重新验证隔离、资源、取消、所有文件工具、快照、独立 grader 和完整链路。旧 H3 证据保留，新结果放在 `evidence/H4/`。

H3 已记录的通用 pytest 项目适配、强杀宿主后的自动容器恢复仍未实现；它们不会阻止本轮单仓窗口/插件接口，但不能据此宣称任意仓库或硬崩溃恢复已经受控。

## 现在的行为

AgentLoop 保留原始对话，用副本构造模型视图；session 在转换前先写 `state.saved`，然后写 `context.prepared`，最后才允许模型调用。masking、摘要及插件文本不会覆盖原始工具观察。非持久运行只有进程内原始历史；需要可恢复证据时必须使用 RunSession。

模型请求前检查消息配对、文本/参数/tool schema 序列化大小及实际配置的最大输出。`none` 同样做检查，超额以 `context_overflow` 终止，调用模型次数为零。非法、重复、孤立或穿插的 tool call/result 以 `context_invalid` 拒绝。

窗口准入采用 UTF-8 字节数加协议余量和预留输出，作为保守配置上界；`estimated_input_tokens` 单列 bytes/4 估计，绝不当作 provider usage 或通用 tokenizer 的精确计数。实际模型窗口必须由使用者配置。未显式配置窗口的旧路径也有 131072 的默认准入额度；Docker 示例显式使用 12000。

| 策略 | 首版行为 |
| --- | --- |
| none | 原文视图 + 请求前额度检查 |
| masking | 只遮蔽旧工具结果；保留调用/结果结构、近期结果、最新失败和近期文件修改；不会强行丢掉保护内容以塞入窗口 |
| summary | 仅本地 extractive fixture；将连续、完整且未受保护的旧工具批次替换为带不可信标记的摘要 |
| mask-then-summary | 先遮蔽，仍超额时使用同一摘要 fixture；仍放不下就拒绝 |

system、user、当前失败和必要调用配对不被摘要删除。摘要记录原始消息区间、来源 hash、持久事件序号（有 session 时）、生成器/版本及独立次数额度。没有模型调用，所以真实 token 用量为 null、模型调用数为 0、模型费用为 0 并标 `no_model_call`。摘要文本不是知识事实库。源 hash 改变即拒绝复用。

## 插件契约

`src/policy/plugin.py` 提供 async `PolicyPlugin.decide(JSON data) -> JSON decision`，wire 标识 `0.1`。no-op 与 fixture 插件可替换；不实现经验检索/失效算法。fixture 只用声明的 valid/repo_revision 验证宿主接受/拒绝行为。

输入是公开任务、观察的角色/hash、仓库版本、预算快照、上次状态；不传 EvaluationSpec、执行器、LLM client、宿主 workspace 路径或私有日志原文。H3 入口把公开 base_revision/base hash 绑定为仓库版本。

候选含 id、text、source、reason，可带 priority、valid、repo_revision。宿主按优先级逐条校验、拒绝过时/无效/超额候选，检查注入后窗口是否仍合法，并分别记录 `requested`、`actually_injected`、`rejected`。候选不会变成 system 指令，注入带不可信来源标记。无论插件要求什么，action proposal 本版都记录并拒绝：`dispatcher_not_enabled`。

未知 major 被拒绝；同 major 新 minor 的可选字段可忽略并记录字段名。所有嵌套 JSON 均检查禁止答案字段、可序列化性及 64 KiB 大小限额。插件异常可降级到无增强视图，记录 `method_degraded`、`policy_error` 类型，不把任意异常文本作为日志泄漏出口。异步插件 await 受同一 run/step deadline 和取消约束。

这是受信 Python 插件的数据边界，不是对恶意进程内代码的隔离。额外工具/LLM 调度尚未开放，不能借本契约声称支持任意第三方插件直接执行或收费。公共原始契约未改写，跨仓真实兼容仍需双方 adapter/版本冻结。

## 恢复

`context.prepared` 原子保存发送视图、原文 hash、转换证据与摘要/插件状态。宿主在写好该事件、尚未调用模型时真实退出后，resume 复用同一视图，不重调插件、不重复 summary 计数、不重复先前文件追加。若模型调用已经启动但没有可恢复响应，继续沿用 H2 的 outcome_unknown，不伪造响应或偷偷重试。

运行指纹包含窗口限额、策略、保护设置、摘要/注入额度、插件版本与 fixture 候选；改变配置拒绝 resume。新 run 清空旧插件状态。持久路径只允许内置 no-op/fixture 插件，原有自定义可执行 hook、plan_act、subagent 的恢复限制不放宽。H3 Docker 中断 resume 的限制保持有效，H4 恢复测试使用受控宿主 fixture 验证事件语义。

## 配置与演示

```yaml
runtime:
  context:
    strategy: masking
    max_tokens: 12000
    keep_recent_tool_results: 3
    summary_max_calls: 1
    plugin: noop
    max_injection_bytes: 4096
```

`plugin: fixture` 时可加 `plugin_candidates` JSON/YAML 列表。旧 `micro_compact: true` 未显式选择新策略时继续走旧保护策略，原始消息仍由 loop 副本隔离；新 `strategy` 优先。

```powershell
.\.venv\Scripts\python.exe scripts/demo_h4.py --output-dir <new-directory>
```

此命令不需要 key、Docker 或网络：同一条长轨迹分别构造四种视图，保留 raw-messages、manifest、results、views、report。示例中 none/masking 因旧 assistant 信息仍过长而拒绝；两个摘要 fixture 可放入窗口，三条插件请求只有一条实际注入。这是机制证据，不是“摘要一定提高修复率”的实验结论。

验收记录见 `evidence/H4/README.md`。真实 LLM 摘要（统一模型账本）、真实 RepoSkill 连接及模型策略效果对照留在后续阶段；本轮不把这些 fixture 当作已完成的真实能力。
