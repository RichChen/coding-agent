# CONTRACT-CHANGE：共享契约补充提案

日期：2026-09-18。状态：**候选 v0.2 讨论稿，未发布、未跨仓确认、未实现**。文件名用于版本化讨论，不表示当前应发送 schema_version=0.2。原始 [v0.1](00_双项目协作与接口约定_v0.1.md) 保持不变。

## 结论与无冲突部分

最终责任分工没有冲突：harness 是唯一预算/执行/有序事件权威，agent 提供策略候选和可序列化状态。无结果的非幂等写不能盲目重放；grader 数据不可进入 agent workspace；两仓用各自 fixture 独立开发。SQLite 和 Docker/Linux 的选择不改变这些语义。

本仓当前没有实现完整公共 DTO/PolicyPlugin，不能称其“已支持”；旧 LoopHooks、ToolResult、TaskResult 和 EventBus 仅是可适配资产。无需等公共细节全部定案才能修复 HP-01/02/03 或独立实现 SQLite fixture。

## 真正需要同步的歧义与建议

| 编号 | 契约/实现冲突 | harness 建议 | 影响与兼容 |
|---|---|---|---|
| C1 | 公共 TaskEnvelope 在所有模式下禁止 expected_files/gold 等；agent 总目标 A1 又保留 diagnostic_oracle 暴露答案的旧路径 | 公共插件 TaskEnvelope 始终不带答案；diagnostic_oracle 先限定为明确标记的 legacy runner。如果未来必须跨仓传 oracle，新增独立 DiagnosticTask 类型/专用端点与 capability，不扩充 realistic metadata | agent 输入/legacy adapter、harness loader。默认拒绝 public DTO 嵌套禁止字段，日志只记字段名/hash。选择保守解释不阻塞真实路径 |
| C2 | “已知 minor 的新增可选字段兼容”与严格输入/防泄漏可能冲突；schema_version 的表示尚未定 | wire 采用字符串 major.minor（如 0.1），文档版本和 wire 版本分别记录；未知 major 拒绝。保留受限 extensions 命名空间，仅接受已注册的可选扩展并限大小；禁止字段即使在 extensions 也拒绝。是否接受更宽的未知字段须两方冻结 | 两仓 DTO、serialized state、fixture；这一收窄若偏离“任意新增可选字段均兼容”，必须用户/协调方同步，不能单方宣称完全 v0.1 兼容 |
| C3 | v0.1 的 EvaluationResult 枚举是 pass/fail/partial/invalid_env；需求同时要求缺少 claim 证据时 unverified | 不新增/混入 grader 枚举；为 RunResult/报告附独立 ClaimCheck 列表，status=verified/contradicted/unverified。未运行 grader 则 EvaluationResult 为 null，另记 evaluation_pending/未验证原因 | harness report/grader，agent 消费者；failure、invalid_env 与 unverified 不混淆，无依据不能指控模型“撒谎” |
| C4 | 旧 success 是 loop 正常结束；旧 repeated metrics 主均值排除 degenerate，无法直接作为公共任务成功率 | legacy success 映射 run termination；只有独立 EvaluationResult 认定 pass。新协议主表使用 assigned 全分母，旧筛选统计放 legacy/条件分析字段；原报告不重写 | harness runner/metrics/report；agent 结果 adapter。新表协议版本区别旧表，旧字段保留 deprecated 映射 |
| C5 | ToolResult(bool)、EventBus 无序号、usage 缺失补 0，与 v0.1 语义不一致 | 新 status/RunEvent/Usage 遵循 v0.1；内部适配旧结构但不能从缺字段推断“已清理/0成本/可恢复”。旧日志只可 replay 证据视图，不能当完整 resume 数据 | harness models/loop/store；agent 读取器。未知 usage=null+provenance，旧 0 值数据标 legacy_unknown，禁止补造真实用量 |
| C6 | 双方同步/异步接口未锁定 | 新主路径 async Protocol + JSON DTO。agent 同步 WorkspaceAdapter 留 legacy，不在宿主 event loop 调 asyncio.run；纯阻塞策略可以受控 offload，但有外部副作用的同步 runner 不能靠线程强取消 | agent async adapter、harness plugin host。若不适配 async，再单独协商 JSONL subprocess bridge，不先实现两套 |
| C7 | v0.1 有 deadline/预算/恢复，但没有明确停机是否计时、resume 是否重置 | 同 run resume 继承已消费额度和绝对 UTC expiry；停机计总时限。进程内使用单调时钟，重启后不复用旧 monotonic 绝对值。若以后允许暂停预算，新增显式 protocol version | harness session/budget，agent policy state。不能在不告知情况下用每次 resume 重置预算提高成功率 |

C2 是需要锁定的兼容策略选择，C1 是两份目标之间的诊断边界歧义，其余多数是旧实现迁移或补充说明。没有向其他任务发送这些提案；由用户/协调方同步后才成为共同接口。

## 最小 DTO 映射（不强制 Python 类名）

| 公共类型 | 本仓目前入口 | 拟做映射/新增 | agent 权限 |
|---|---|---|---|
| TaskEnvelope | EvalRunner 的 task dict、AgentLoop.run(description,id) | 新 public parser + 旧任务 loader 的显式字段提取，固定 repo/base、workspace/profile/budget/mode/repeat | 仅公开对象，不含 EvaluationSpec |
| RunEvent | EventBus.emit(event,**payload) | 新宿主单写者封装稳定 ID/seq/op/attempt/UTC/elapsed；legacy JSONL exporter | 只提交候选 event，不能分配 seq |
| Tool request/result | ToolCall、ToolContext、ToolResult | validated args 与内部 metadata 分开；status、deadline、output refs、cleanup 和副作用类别 | 只经 action proposal 调用 |
| PolicyInput/Decision | LoopHooks（非合格插件边界） | async decide，当前计划/公开观察/预算/state → 候选文本/来源/理由/state/metrics/proposals | 不持有可任意调用的执行器/LLM client |
| ArtifactRef | 字符串 trace_file/内联 output | run 归属、唯一 ID、hash/媒体类型/bytes/敏感级别、受控引用；拒绝跨 run 路径 | host 解析/授权后读取 |
| Usage | LLMResponse.usage dict、total_tokens | reported/estimated/unknown，按主模型/summary/controller/builder/grader 分账和总账；价格版本/币种/nullable cost | 所有线上调用走宿主；离线构建另记 |
| RunResult/EvaluationResult | AgentRunResult + TaskResult | run termination 与 grader 状态分离，连接固定 manifest/trace/patch/test evidence | 私有验证结果不自动进入未来 memory |

受信插件只获得净化的公开数据。进程内协议不是对恶意插件 Python 代码的隔离保证；任意第三方不可信插件执行不在首版范围。

## 契约 fixture 计划与双方责任

下表是预期结果合同，实际 JSON fixture 尚未落地。计划放 `tests/fixtures/contracts/v0.1/`，首次同步由用户/协调方分发同版本内容 hash；本轮不修改对方目录。

| fixture | 预期不变量 | 主验收位置 |
|---|---|---|
| read → patch → public test → grader | run_id 串起证据，只有 grader pass 可计成功 | H3；agent 适配映射 |
| 非法参数 | tool execution_count=0，错误原因可读 | HP-01，两仓 adapter |
| 中途取消 | 无后续写；unsupported profile 先拒绝 | HP-03/H3 |
| 写后崩溃 | 不重复 append，unknown 或有证据核对 | HP-04 |
| 有效/过时经验 | fixture 插件按给定决策注入/拒绝，记录来源/原因 | harness H4 验接口；agent A3 验失效算法，不能拿 harness fixture 代替算法验证 |
| oracle sentinel | realistic DTO/prompt/工具可见 workspace 均无 sentinel | H3 + agent A1 |
| 长插件候选 | requested 和 actually_injected 数量/来源不同且可解释；不绕预算 | H4 |
| schema compatibility | 未知 major 拒绝、可选 minor 扩展按锁定规则处理；禁止 oracle 字段不可通过 | 两仓 contract tests |

## 迁移与退出条件

1. 保留旧配置/日志/报告，新增能力和协议版本明确，不批量改写历史结论。
2. 单仓以 no-op/fixture 实现并标明已支持/stub/未支持；未实现的插件策略不宣称支持。
3. 首次联调前锁定上述 C1/C2/C6 及双方 commit/adapter/wire 版本；若决定破坏性变更，先补逐字段迁移和旧数据读取规则。
4. fixture 通过后再做一个真实连接任务；外部后端 unavailable 不回落到裸宿主标绿，插件故障可 no-op 但 method_degraded/policy_error 计入报告。
