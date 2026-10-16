# coding-harness 总修改目标 v1.0

日期：2026-09-18。目标仓库：`D:\crq\src\coding-harness`。

对应 Codex 任务：[改造coding-harness](codex://threads/01a0b3a8-2038-7ed1-93ca-01ff458abbf8)。

配套必读：[双项目协作与接口约定 v0.1](00_双项目协作与接口约定_v0.1.md)。本文件是最终形态与验收目标；具体实施计划由项目对话核对代码后制定。收到本文件的首轮仅做理解、代码核对、文档和计划，不立即实施源码变更或付费评测。

## 1. 一句话目标

把现有 Python coding-agent runtime 和 eval harness，升级为一个**可取消、可恢复、可测量，且能验证任务实际完成情况的 Agent 执行与评测系统**；它是用户面向 Agent Infra / Agent Runtime / Harness / LLM 应用后端日常实习的主项目。

用户最终应能从真实源码讲清一次模型调用到工具执行的完整生命周期，用故障演示说明正确性，用相同底座的对照实验证明设计的收益与代价。并不要求达到大厂生产规模，也不预设复杂配置一定优于简单基线。

## 2. 为什么这样改：岗位和技术证据

### 2.1 岗位锚点

| 官方岗位 | 可核验要求 | 本项目应提供的证据 |
|---|---|---|
| [字节 Agent Infra 后端 A238339](https://jobs.bytedance.com/campus/position/7671205707161422133/detail) | Python/Go/C++ 至少一种；Runtime、编排、状态、Sandbox、Memory、轨迹、并发、资源效率、可观测性 | 可恢复运行循环、工具生命周期、隔离后端、trace、故障与并发实验 |
| [字节 Agent开发 A213505A](https://jobs.bytedance.com/campus/position/7594738744131733765/detail) | Harness/Runtime、工具、上下文、异常恢复、稳定性和完成率 | 清晰 API、上下文策略、失败分类、端到端 repair demo |
| [字节 Agent Harness 算法 A242905A](https://jobs.bytedance.com/campus/position/7677984300810438917/detail) | Context、Tools、Harness 评测，另有 multi-agent/advisor/RL loop 等职责 | 首先证明组件评测和 grader；后面几项是拓展方向，不因 JD 出现就全部实现 |

招聘样本以已核验的字节页面为主；腾讯和阿里只完成部分官方列表核验。不能声称已调查完全国大厂，也不能把未读取的任职要求当作设计依据。架构与任务相关度不是录用概率。

### 2.2 技术来源如何影响设计

以下承接既有 2026-09-18 调研，当前任务没有重新联网复核，也没有复现这些工作的实验数字。

- [Managed Agents](https://www.anthropic.com/engineering/managed-agents)：借鉴 session、harness、sandbox 分离；落实为持久日志、运行循环和执行后端三个独立责任。
- [OpenHands SDK v1.49.0](https://github.com/OpenHands/software-agent-sdk/releases/tag/v1.49.0)、[v1.49.2](https://github.com/OpenHands/software-agent-sdk/releases/tag/v1.49.2)：借鉴会话容器生命周期与插件边界。采用时重新确认版本兼容和 API，不能直接从 release notes 推断本项目已具备隔离。
- [Deep Agents 0.7.15](https://github.com/langchain-ai/deepagents/releases/tag/deepagents%3D%3D0.7.15)：借鉴工具输出外置标识与子任务状态传递，防止不同调用覆盖同一 artifact。
- [Harness Design 实证研究](https://arxiv.org/abs/2609.20804)：设计同模型、同任务、同预算的组件消融；不把论文中的某策略结果当作本项目必然结果。
- [Working Memory 测量研究](https://arxiv.org/abs/2608.31057)：分别衡量存储状态、实际发送上下文、管理开销和任务结果。
- [Infrastructure Noise](https://www.anthropic.com/engineering/infrastructure-noise)：固定并记录 CPU/RAM、并发、超时、容器和网络条件，避免把环境优势算成算法优势。
- [LoopsBench](https://github.com/microsoft/Loopsbench)：后续增加依赖任务和历史功能回归保持；先做小型自建场景，不能冒充官方 benchmark 复现。
- [OverclaimBench](https://arxiv.org/abs/2609.20812)：启发最终声明与 trace 证据核对；命令退出 0、文件读过均不是任务正确性的充分条件。

## 3. 当前资产和需要复核的差距

已存在：异步 AgentLoop、工具注册、policy、预算、重试、JSONL trace/EventBus、planner、只读一级 subagent、observation masking、judge 和 eval/report。优先保留其可用部分、配置和历史证据，不进行无必要的全仓重写。

此前审计记录以下风险，项目对话应在实施前复核最新源码，不机械假设仍未修复：

| 范围/当前入口 | 既有审计发现 | 目标 |
|---|---|---|
| `src/llm/client.py` | stream_chat 等完整响应后再伪装 delta；每次新建 HTTP client | 真实增量语义、可复用 client、显式关闭 |
| `src/runtime/loop.py` | tool 参数 JSON 解析失败可能变成空对象；增量拼接语义需核对 | 严格校验、错误可见、部分响应不得执行 |
| `src/tools/command.py` | 超时后进程树清理和输出峰值限制不足 | deadline 内取消、终止与回收、边读边限量 |
| `src/policy/sandbox.py`、`limits.py`、`budget.py` | path guard 不等于 OS 隔离；全局超时不能只在循环间检查 | 能力声明、独立后端、可强制取消 |
| `src/tracing/*`、`runtime/state.py` | trace 主要是事后记录 | 可参与控制与恢复的事件状态模型 |
| `runtime/compact.py`、`context.py` | 观察遮蔽不等于摘要或 checkpoint | 原始日志与模型视图分离，多策略可替换 |
| `src/eval/*` | 需要强化同预算、环境条件和实际验证证据 | manifest、独立 grader、全成本、逐任务结果 |

本次只读检查发现 `docs/changes/SOLID-D2-REMAINING-CLOSEOUT.zh-CN.md` 有未提交修改，应视为用户工作予以保留。`AGENTS.md` 指定的参考路径 `C:\Users\23500\Desktop\src\learn-Codex-main` 本机检查不存在；先检查相关已知项目目录是否有迁移版本，记录参考不可用，依现有源码完成计划，不虚构已读参考实现。缺失参考不会阻止不依赖它的文档/诊断工作。

## 4. 最终使用体验

一个新同学按 README 可以在没有模型 key 时运行离线故障 demo；配置 key 后在明示预算内运行单个真实修复任务。运行输出目录包含 manifest、事件流、artifacts、独立验证结果和报告。

典型演示链：

1. 在隔离 workspace 中接收公开 issue 和固定仓库版本。
2. 使用模型与受控工具读文件、定位、修改、运行公开测试。
3. 过程中展示 token/耗时、工具失败和上下文管理事件。
4. 可取消任务并验证进程已停止；可在受控中断后恢复，重复写风险有解释。
5. agent 结束后由独立 grader 验证修复与回归，再生成“做了什么、证据在哪、还没验证什么”。
6. 使用同一任务和运行配置切换 context 策略或 RepoSkill 插件，输出逐任务差异和全成本。

这些是预期能力；CLI 名称、flags、目录布局由实施计划决定，不能把未实现的示例命令写成已可运行。

## 5. 架构目标

```text
CLI / 可选薄 API
  ├─ TaskEnvelope + Config + Budget
  └─ Runtime / SessionController
       ├─ ModelGateway（stream / retry / usage / cancel）
       ├─ ContextView（mask / summarize / artifacts）
       ├─ 可选 PolicyPlugin（coding-agent 提供）
       ├─ ToolRegistry -> PolicyCheck -> ExecutionBackend
       └─ EventStore + StateReducer + Checkpoint

agent 终止之后：EvaluationSpec -> 独立 Grader -> Result / Report
```

模块可以复用现有类，不必按图新建大量抽象层。重点是依赖方向和语义清楚：模型给出的结束回答与 grader 认定成功分开；插件无权绕过执行策略；session log 不因窗口压缩而丢失。

## 6. 核心需求与行为验收

### H1 模型网关正确性

- 真实 stream 按 content/tool index 和 ID 聚合片段，处理多 tool call 交错、分段 JSON、最终 usage、异常中断；不假设每个 chunk 是完整 JSON。
- tool arguments 在完整形成并通过 schema 后才能执行。非法 JSON、缺字段、超长参数分别记录，不静默改成 `{}`。
- 非流式是独立、诚实命名的路径。某 provider 不支持 streaming 时显式能力降级，不能伪造延迟指标。
- HTTP client 生命周期按 run/service 复用，连接数有界，正常/异常/取消均释放。
- 重试区分限流、暂时网络故障和参数错误；退避受总 deadline 约束，所有尝试计量。收到部分 tool stream 后不能先执行再重试重复执行。

验收：用可控本地流模拟完整、分裂参数、交错调用、中途断流和取消；记录首个真实 chunk 时间；断流不得执行未完成工具。单测无需真实 API；provider 集成另标记且有预算。

### H2 工具治理、取消与资源边界

- 定义 schema validation、policy check、intent、execute、observation 的顺序。
- 全局 deadline、step timeout、tool timeout、用户取消传播到正在执行的 HTTP/子进程。
- 进程清理明确支持平台：推荐 Linux 容器作为受控执行目标，Windows 提供宿主开发/离线测试；若实现 Windows 执行则需 process-tree cleanup 方案和测试，不宣称未测试的跨平台保证。
- stdout/stderr 边读取边限量；可保存有限 artifact，记录截断，不能 collect 全量后才截断。磁盘也有总量上限。
- 环境变量采用明确 allowlist，空列表语义不能意外继承全部 secrets。日志脱敏；密钥不进入命令行、trace 或模型可见内容。
- 工具按 read-only、可幂等写、非幂等副作用分类。自由 shell 不能默认视为可重试。

验收：长进程派生子进程并尝试延迟写 marker，取消/超时后观察约定窗口内无继续写入；大输出不导致无界内存；环境探针只看到允许变量。测试使用临时目录、假凭据，不读取真实 secrets。

### H3 持久事件与恢复语义

- 至少支持单机持久存储；SQLite transaction + artifact 文件，或具有明确刷盘/损坏恢复策略的 append-only log 均可。实现者说明选择，不强制 Kafka/Redis。
- 有稳定 run/operation/attempt ID、顺序号、版本及终止状态。checkpoint 是加速恢复的派生状态，不覆盖原始事件事实。
- 明确崩溃窗口：意图落盘前、意图落盘后/执行前、执行后/结果落盘前、结果落盘后/checkpoint 前。
- “执行后未落盘”的写操作进入 reconcile/outcome_unknown；对于可校验写操作比较内容 hash/外部幂等 key；无法判断时停止该动作并标记，不能盲目重放。
- 不承诺跨任意外部系统的 exactly-once。日志落盘与外部副作用通常无法形成统一事务，文档必须讲清这一点。
- 恢复时检查 workspace、代码/配置/schema/backend 状态及 artifact 是否仍存在。缺失或不兼容有明确拒绝原因。
- replay 表示重建状态/证据，不重新执行外部动作；resume 才继续尚未完成工作，二者区分。

验收：至少四个崩溃窗口有确定性故障注入；同一追加动作不重复执行；不确定状态能被准确报告；损坏尾部日志、重复事件和 checkpoint 过期有定义行为。单 run 并发启动恢复应有锁/租约或明确拒绝，避免双执行。

### H4 一个真正受控的执行后端

- 先实现一个后端即可：本地 Docker，或固定版本 OpenHands SDK 的受控执行适配，二选一并验证；不要求同时实现。
- 会话创建、workspace 挂载、命令执行、取消、销毁各有行为与失败处理。
- 限制 CPU、内存、可见文件和网络，具体支持能力写入 profile；不用 privileged，不把 Docker socket 和宿主凭据挂给任务。
- 明确容器不是绝对安全边界。宿主 path policy 继续保留，名称与实际保证一致。
- 后端不可用时集成测试说明 unavailable，不静默切回裸宿主并标绿。

验收：外部路径不可读写、网络按配置开放/阻断、资源超限结果可解释、取消/清理不遗留任务进程。真实后端集成至少一次通过并保存版本/日志；只有 mock 不能宣称已完成。

### H5 上下文窗口与原始事件分离

- 支持可切换的 `none`、observation masking、summary、mask-then-summary 四种策略。`none` 仍须在模型调用前识别溢出并终止/报告，而非送出非法请求。
- 保留 system/task 约束、未完成状态、必要 tool call/result 配对；不得产生引用不存在调用的 tool message。
- 外置输出按唯一 artifact ID 管理，读取受权限和预算约束；内容 hash、大小、过期状态可查。
- summary 需要来源事件范围、生成模型、版本和成本。保留错误摘要导致的失败样本，不把摘要当作可信事实库。
- provider usage 为主要实测依据；chars/4 只能标 estimated。状态存储量、实际发送量、管理调用开销分别计量。

验收：同一条超长轨迹对四种策略给出合法消息结构、可解释截断/摘要和完整原日志；多调用 artifact 不互相覆盖；管理成本进入总账。

### H6 可观测性与独立评测

- trace 能回答“哪个输入、哪个工具、什么错误、用多少资源、为何停止”，提供机器可读 JSONL/JSON 和简洁 Markdown/HTML 静态报告。dashboard 先做到报告可浏览即可，不优先做前端工程。
- success 由独立 grader 赋值。测试计数为零、缺依赖、测试收集失败、测试被删除或绕过都不能靠 exit code=0 算通过。
- hidden tests/gold 不在 agent 可读 workspace。agent 可执行公开测试，验证方使用固定来源的回归测试，记录 patch 对测试文件的修改。
- 结果包含任务成功率、终止原因、tool failures、tokens、total cost、wall time、环境失败。p95 需报告样本数，小样本标探索性。
- completion claim 检查只核对能验证的声明，例如对应的测试命令、计数和结果；不能把“没有查到证据”一律称为谎言，应支持 unverified。

验收：错误 final answer 不能把失败任务变成功；只打印“all tests passed”无效；删测试或 pytest 未采集案例会被拒绝/标异常；报告可从原始结果重生成。

### H7 与 coding-agent 的最小集成

- 提供可选 PolicyPlugin 边界和公共事件/结果 schema，参照共享契约。
- 不在本仓库实现 SkillCard 知识库、记忆合并或版本失效算法。
- 首先用 no-op 和 fixture 插件验证；随后连接 agent 的一个 skill/memory 插件。
- 集成后所有模型调用、工具和上下文注入经过统一预算、policy 和 trace；插件故障可回退，但必须记录 method 降级。

验收：一个任务同底座切换插件开/关，报告注入证据与运行差异；兼容版本明确，单仓测试不依赖另一个未完成仓库。

## 7. 阶段优先级与首个可投递版本

| 阶段 | 交付 | 阶段通过条件 |
|---|---|---|
| H0 现状冻结与计划 | 差距表、已知失败基线、契约映射、具体任务包 | 保留脏修改，区分旧证据与新目标 |
| H1 执行正确性 | 模型网关、schema、取消、输出边界 | 可复现旧故障的针对性测试通过，无需付费模型 |
| H2 会话可恢复 | event/state/checkpoint、幂等/unknown 语义 | 崩溃窗口演示、replay/resume 区分成立 |
| H3 真实后端与最小评测 | 一个后端、独立 grader、基础 manifest/report | 一次真实执行隔离与清理演示；零测试不能成功 |
| H4 上下文与策略接口 | 四种 context policy、usage、fixture 插件 | 单策略可切换、成本完整、contract 测试通过 |
| H5 联调与小规模证据 | RepoSkill 插件、真实修复/故障案例、结果分析 | 受限预算下端到端与配对结果可追溯 |
| H6 可选增强 | API、长任务、进一步调度/benchmark | 仅在核心稳定且目标岗位需要时实施 |

首个可投递版本重点完成 H1–H3、H4 的接口/基础策略和至少一个真实端到端任务；四策略全面实验与跨仓联调随后补齐。无需等到所有研究结果正向才开始投递。

## 8. 实验合同草案

### E-H1 可靠性：这是工程验收，不是假设模型更聪明

固定本地 mock provider、工具 fixture 和资源 profile。故障覆盖非法 JSON、流中断、429/5xx、deadline、子进程、高输出、日志尾部损坏、写后崩溃与恢复竞争。

成功信号：支持的场景满足 H1–H4 行为不变量，且留下可复现证据。失败信号：超时后仍写入、恢复重复副作用、未知结果被报成功、日志静默丢失。

并发先测 1/5/10，硬件允许时再测 50；主要用本地可控服务，区分 provider 限流和本机瓶颈。记录吞吐、p50/p95、失败率、内存/进程峰值、取消收敛耗时。50 并发是可选压力档，不是必须花真实模型费用达到的 KPI。

### E-H2 上下文策略对照

问题：紧窗口下 masking/summary 是否降低 overflow，同时改善总成本与任务完成率？

固定：同一模型标识、task list、基础 prompt、tool 集、backend、资源、预算、temperature、repeat/seed 策略，仅切 context policy。不同窗口预算单独分层，不能混起来报单个收益。

比较：none / masking / summary / mask-then-summary。首轮只选两个有明确差异的策略做 pilot，再按预算扩展四组，避免同时加入 planner/subagent/新模型。

初始建议：5 个任务做连通 smoke，不用于收益主张；冻结 12–20 个任务做 pilot，至少 3 次 repeat 的预算估算，无法承担时减少并如实报告样本。provider 不支持 seed 时记录采样不确定性。

主指标：独立验证成功率和 total cost（分别报告，不随意合成总分）。次指标：overflow、summary 次数、offload/读取次数、延迟、发送上下文、环境失败。

支持信号：同预算下失败率减少且非仅靠增加总调用，或任务表现接近但成本明确降低。失败信号：摘要丢关键约束、管理开销超过节省、收益仅来自单任务、环境条件不一致。研究负结果不使工程交付不合格。

统计：逐任务配对差异；repeat 不当成互不相关的新题；按任务或仓库分组 bootstrap，仓库太少时说明区间不可靠。预先冻结 task manifest、候选集、分母、成本口径、重复规则，再跑正式对比。

### E-H3 可选连续任务

自建三个相互依赖开发单元，在后续阶段重跑此前回归测试，并在中途注入一次中断。评价完成单元数、regression retention 和恢复结果。它是 LoopsBench 启发的 demo；只有实际按官方协议跑过，才可写官方基准结果。

## 9. 产物与完成定义

至少交付：

- 架构与状态机说明：源码位置、依赖方向、恢复边界、支持平台。
- 可执行离线 demo，以及一个有预算配置的真实任务入口。
- 针对高风险行为的测试和真实后端集成证据；不追求无意义覆盖率数字。
- experiment manifest：代码版本/未提交 diff hash、配置、模型、预算、数据 hash、backend/image、资源、环境。
- events、artifacts、results、报告与失败案例，脱敏且可再生成。
- 至少三篇短 case study：超时清理；写后崩溃；上下文策略成功或负结果。
- 面试解释文档：90 秒项目介绍、5 分钟架构、10 分钟故障复盘，全部引用真实实现和证据。

没有“成功率必须达到 80%”“一定比某框架强”的预设验收线。对支持场景的正确性是硬验收；模型能力提升是需实验验证的假设。

## 10. 当前不纳入核心范围

不要求 Java、Kubernetes、多租户平台、GPU serving、自训练模型、大规模 RL、多种 sandbox 同时支持、复杂前端、海量 benchmark 全跑、MCP/A2A 协议大礼包。FastAPI 可以在核心稳定后做 run/status/cancel/events 的薄层，不先围绕 Web 产品重构 runtime。

已有 planner/只读 subagent 保留并准确命名，必要时作为单独消融；不为了“多 Agent”在首版增加一串同质角色。

## 11. 实施者的首轮响应

按共享契约第 9 节输出计划。尤其列出：当前高风险点是否仍存在；单机事件存储选择；Linux/Windows 支持矩阵；一个执行后端的选择理由；最先做的 2–4 个独立任务包。

对每个任务包同时给出直接 Codex 实施与转交 Cursor 所需的同一套验收条件。无需用户现在选择工具就能把计划写完；暂不启动实现。

## 12. 依据与证据纪律

原始本地依据（同一工作区 outputs 目录）：`coding-agent与coding-harness项目审计与技术调研.md`、`2026年9月Agent业界学术更新与项目升级建议.md`、`国内大厂Agent日常实习岗位调研_2026-09-18.md`。

最后一份岗位报告中的全国覆盖、岗位匹配以及改造建议具有初步性，本目标文档已将其收敛为明确优先级。实现 API 和正式引用论文具体结论前按需回查原始来源；没有读过的正文、没运行的 adapter、没完成的实验不写成已验证事实。

当新代码与旧审计不一致，以可复核现状为准并记录修正。不隐藏旧负结果，不覆盖历史报告来制造进步，也不把路径白名单称为 OS sandbox、把 fake adapter 下的真实模型调用称为已运行 OpenHands。
