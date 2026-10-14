# coding-harness 实施计划 v1.0

日期：2026-09-18。本文首发时状态为 H0 计划交付，**未开始产品源码改造**。截至 2026-09-21，R1 已按本计划范围收口；当前实现和证据以 [R1 收口记录](R1-CLOSEOUT.zh-CN.md) 及各阶段 evidence 为准。适用仓库：`D:\crq\src\coding-harness`。本计划适用于 Codex 直接实现和 Cursor Agent 承接，验收标准相同。

## 1. 目标、责任与本轮边界

R1 后续的独立窄范围见 [R2-lite 真摘要契约与任务包](R2-LITE-TRUE-SUMMARY.zh-CN.md)。它扩展受控真实摘要与离线验证，不重新打开 H1–H5 收口项，也不启动通用 grader、H6 或付费实验。

最终交付一个单机 Python Agent Runtime/Harness：接收公开任务与固定仓库版本，在统一预算和权限下调用模型、执行工具，能取消正在运行的工作，能从持久事件重建状态并保守恢复，并由执行循环之外的 grader 判断任务实际完成情况。每次运行留下可追溯的输入、事件、输出、使用量、环境与验证结果。首先证明正确性与最小证据闭环，不预设策略改造必然提高成功率。

本仓库负责模型网关、执行治理、后端生命周期、持久事件、恢复、窗口管理、artifact、资源计量、独立验证及报告。coding-agent 负责未知 issue 定位、Skill/Memory 数据与来源、失效/冲突规则、Router、经验抽取及其专用实验；harness 仅接受有来源的策略候选并决定是否执行/注入。保留现有 planner 和一级只读 subagent，但不增加角色团队。

不建设 Kubernetes、多租户/队列平台、通用 Web 产品、向量数据库集群、模型训练/RL、多种隔离后端或全量 benchmark。没有模型预算就不运行真实调用。当前不改对方仓库、不发跨任务消息、不提交/推送。

配套文件：

- [本仓总目标 v1.0](01_coding-harness_总修改目标_v1.0.md)、[共享契约 v0.1](00_双项目协作与接口约定_v0.1.md)、[协作方总目标 v1.0](02_coding-agent_总修改目标_v1.0.md)：原文存档，不在副本中自行改变共同字段含义。
- [现场基线与核实命令](BASELINE-EVIDENCE.md)：环境、测试结果、只读反例及来源 hash。
- [首批四个任务包](TASK-PACKAGES.md)：可直接交接，含范围、输入输出、行为验证、命令、产物和退出条件。
- [契约冲突与兼容提案](CONTRACT-CHANGE-v0.2-PROPOSAL.md)：待用户/协调方同步的解释，不是已发布的新契约。

## 2. 冻结点与证据范围

核对 HEAD：`1f5903b620895ad8af3289ffeae529c15c3576a0`，提交说明 `docs(d2): demo script and interview materials A-D closeout`。本次“最新源码”指此本地 HEAD 加当前工作区；没有 fetch，未声称核对远端最新版本。

起始 `git status --short` 仅有 `docs/changes/SOLID-D2-REMAINING-CLOSEOUT.zh-CN.md` 修改。本轮保留其内容，hash 见基线文件。`docs/upgrade/` 起始不存在，三份源文档用文件编辑工具新增后逐字节 hash 一致。

已完整读取根 `AGENTS.md`。指定参考 `C:\Users\23500\Desktop\src\learn-Codex-main` 不存在；候选 `D:\crq\src\learn-Codex-main`、`C:\Users\Administrator\Desktop\src\learn-Codex-main` 也不存在。`D:\crq\src` 下发现的是 `learn-claude-code-main` 与 `learn-fastapi-langgraph`，不把它们当作同一参考实现，未宣称阅读 `s_full.py`。缺失参考不阻塞本轮本地诊断和规划；开始写新 agent 代码前再核对指定参考可用性，仍不可用则记录限制，沿现有模块实现。

现有 148 个测试在本机的实际结果为 **117 passed、31 skipped、1 warning**；跳过由缺少 `pytest-asyncio` 触发。不能引用历史文档的“148 passed”作为当前完整基线，也不能凭旧测试通过宣称新正确性成立。未安装依赖、未使用真实模型、未启动容器或下载数据。

岗位与论文链接保留为目标文档的背景线索；本轮没有重新联网核验或复现。岗位具体证据主要为字节 JD，不能称全国覆盖；协作方历史分数不属于本仓新实验。本计划主要依据以下当前代码。

## 3. 源码差距：保留资产、修复风险、新增能力

行号属于上述冻结点；改动后以符号名重新定位。这里的“缺失”指已检查 `src/`、现有脚本和测试中没有符合目标的实现。

| 项目 | 当前证据：文件 / 符号 | 复核结论与影响 | 落点 |
|---|---|---|---|
| 装配和配置 | `src/harness/factory.py:73 build_agent`；`src/config/schema.py:111 HarnessConfig` | 已有集中装配、Pydantic 配置校验，可复用；配置校验不等于工具参数校验 | H1–H4 局部扩展 |
| 模型传输 | `src/llm/client.py:136 chat`、`:162 AsyncClient`、`:186 stream_chat` | 每次 chat 新建 client；stream 先 await chat 再产出完整事件，仍是骨架，无真实首 chunk 延迟 | HP-02 |
| 参数正确性 | `src/llm/client.py:219 _parse_response`、`:235 args = {}` | 非法 JSON 仍变空对象；只读反例已复现。合法 JSON 的数组/null 也未被统一拒绝 | HP-01 |
| 聚合和终止 | `src/runtime/loop.py:133 _call_llm` | 文本 delta 覆盖而非拼接；tool delta 每次 append 完整调用；流 EOF 即返回，无完成标记校验。接真 SSE 前必须一起改 | HP-02 |
| 工具边界 | `src/tools/registry.py:28 schemas`；`src/runtime/loop.py:364` 起工具循环；`src/tools/base.py:36 ToolResult` | schema 只发给模型；loop 直接修改参数注入 `_call_id` 后执行；执行端无统一 required/type/length 检查。结果仅 success/error，无副作用类别 | HP-01 / HP-03 |
| enabled_tools | `AgentLoop.run` 先过滤 schemas，执行却用 `ToolRegistry.get` | 工具已注册但未启用时仍可被伪造调用请求命中；当前 factory 通常仅注册启用工具，但公共 loop 不能依赖这一偶然条件 | HP-01 |
| 重试 | `src/runtime/retry.py:29 should_retry`、`:45 execute` | 已按 HTTP 429/5xx 与 4xx 区分，不能说完全没有分类；但退避不受剩余总时限约束，attempt/失败 usage 未统一记录 | HP-02 / HP-03 |
| 取消和 deadline | `src/runtime/loop.py:122 _check_cancelled`、`:229`、`:343`；`src/policy/budget.py:36 start_step`、`:52 check_step_timeout` | 仅在循环/工具批次边界检查；不能打断正在等待的 HTTP 或工具；同批多工具间不检查。取消返回还丢失已累计步骤与用量 | HP-03 |
| 命令生命周期 | `src/tools/command.py:150/:192 proc.communicate`、`:154/:196 timeout`、`:253` 截断 | 超时仅返回，未 terminate/kill/wait；stdout/stderr 全量收集后才截断；无外置总量上限。风险由源码确认，本轮没有生成失控进程演示 | HP-03 |
| 环境变量 | `src/tools/command.py:54 _build_subprocess_env`；`src/config/schema.py:75 CommandConfig` | 空白名单返回 None，实际继承全部环境；只读探针已复现。非空白名单现有过滤可复用，但系统变量例外要明确 | HP-03 |
| 隔离 | `src/policy/sandbox.py:20 Sandbox` / `resolve`；`src/tools/command.py execute` | 文件工具有路径守卫与 symlink resolve；shell 只设置 cwd。没有 OS 文件、网络、资源隔离，不能称完整 sandbox | H3 后端 |
| 持久性 | `src/tracing/events.py:27 open` / `:36 emit`；`src/tracing/logger.py:26 open_run`；`src/runtime/state.py:20 AgentState` | flush JSONL 日志但无事务/恢复 reducer；毫秒/秒文件名、写模式 w 无稳定 run/seq/op/attempt；StepRecord 只存消息数与截断结果，不足以恢复完整会话 | HP-04 |
| 上下文 | `src/runtime/compact.py:128 micro_compact_openai_messages_with_stats`、`:17 estimate_tokens`；`src/runtime/context.py:51 build_context_hooks` | masking 已保护最新失败/近期修改及 tool 配对，可保留；在消息列表上原位替换，原始内容未有权威保存；summary/offload/硬溢出检查缺失 | H2 原日志、H4 视图 |
| 总预算与子运行 | `src/tools/subagent.py:121 Budget`、`:143 total_tokens`；`src/runtime/loop.py:296` | 子任务独立 budget 和 trace，父结果没有累计子模型 usage；没有 token/call/货币全局上限。默认先禁用子任务；启用必须经过共享账本 | H1 基础、H4 汇总 |
| 现有裁判 | `src/eval/runner.py:264 _explain_expected`；`src/eval/metrics.py:133 aggregate_metrics` | 已区分 loop success 与 expected_check，非单纯最终回答判成功；原有文件/AST/命令裁判可作为 legacy 保留 | H3 兼容 |
| 测试真实性 | `src/eval/runner.py:355 _explain_command_success`、`:509 _run_shell_command` | pytest_passes 映射成 exit code/关键词；无可信采集数量/测试身份/篡改检测，同步 subprocess 阻塞异步 runner，超时清理也不充分 | H3 独立 grader |
| Oracle 边界 | `src/eval/runner.py:221 _copy_fixture_dir`、`:239 _restore_protected_paths`、`:106 _run_task` | 已跳过顶层 `.oracle`，传给 loop 的是 description，不能说 expected 直接进 prompt；但无 PublicTask DTO，初始文件/嵌套 oracle/宿主 shell 仍缺物理边界；恢复 protected_paths 不记录原始篡改 | H3 契约和双 workspace |
| 统计分母 | `src/eval/metrics.py:174 aggregate_repeated_metrics`、`:186 valid_runs` | 主均值排除判为 degenerate 的轮次；只读两轮反例输出 100%，全分母应为 50%。保留旧报告，新协议修正并单列条件统计 | H3 报告 |
| 使用量与报告 | `src/llm/client.py _parse_response`；`scripts/run_eval.py main`；`src/eval/report.py ReportGenerator` | 缺 usage 被填 0；价格单一每千 token；报告已有配置 hash/commit/逐任务矩阵，未知 cost 现有显示 n/a 可复用；欠缺 attempt、原始结果重生成、环境/diff/data hash | H1/H3/H4 |
| 插件 | `src/runtime/hooks.py:23 LoopHooks` | 已有异步 hook，但直接获得可变 messages/workspace，不是有预算/来源/序列化状态的 PolicyPlugin；当前公共契约均未实现，不标 stub 已支持 | H4 |

## 4. 技术选择与支持矩阵

### 4.1 首版模块关系和执行顺序

```text
公开 TaskEnvelope ──> SessionController / AgentLoop
                         ├─ shared Budget + ModelGateway ──> ContextView
                         ├─ PolicyPlugin(no-op/fixture) ──> 候选/受控 proposal
                         ├─ schema → policy → durable intent → ExecutionBackend
                         └─ EventStore(SQLite) → StateReducer → Checkpoint
                                   └─ ArtifactStore → JSONL 导出

run 终止 + patch ──> 独立 grader workspace + EvaluationSpec ──> EvaluationResult
manifest + events + results ──> 可重生成静态报告
```

名称是职责划分，不要求每框都新建服务。复用 `AgentLoop`、`build_agent`、已有工具和报告入口；按需新增 `src/contracts/`、`src/execution/`、`src/runtime/session.py`、`src/tracing/store.py` 等小模块。源日志先保存，再构造模型视图；插件不可直接执行或向数据库写有序事件。grader 在 agent 停止后执行，不经模型自评赋分。

### 4.2 本地持久存储：SQLite + 有界 artifact

选择 Python 标准库 SQLite；减少依赖，事务能一次提交事件和派生状态游标。首版单机单写者，不用 Redis/Kafka。仅支持本地磁盘，不在网络共享上承诺锁/WAL 语义。数据库为事实来源，JSONL 为可重生成导出，避免数据库和日志双权威。

计划约束：`(run_id, seq)`、event_id 唯一；operation_id 在逻辑动作间稳定，attempt_id 每次尝试新增。事务提交 intent 后才交给执行器；结果和预算结算可在同事务提交。artifact 先以唯一 ID 写临时文件、计算 hash、完成发布后提交引用；孤儿文件有配额及回收规则，引用缺失须报错。checkpoint 记录 schema、最后 seq 和事件摘要，不能删除事实事件。

恢复的四个窗口：

| 崩溃位置 | 可证明的事实 | 恢复动作 |
|---|---|---|
| intent 提交前 | 控制顺序保证未派发执行 | 允许正常调度一次 |
| intent 后、实际执行前 | 外部观察仅知 intent；崩溃恢复通常不能证明是否执行 | 保守看作未决，检查执行凭据/目标状态；不能因测试注入点已知就替真实恢复猜答案 |
| 执行后、result 提交前 | 副作用可能已发生，日志不能与外部写原子提交 | 可核对写用前/后 hash、原子替换或幂等 key；自由 shell/append 不自动重放，outcome_unknown |
| result 后、checkpoint 前 | 已提交结果是权威 | reducer 重建，跳过该动作，更新 checkpoint |

replay 只重建状态和证据，执行器调用数必须为 0；resume 才继续新动作。恢复前校验 workspace/base/config/code/schema/backend/artifact，失败给明确原因。首版可用单 run 排他锁拒绝竞争恢复；不能仅依赖会过期的租约，导致旧 worker 未死而新 worker 重复执行。恢复占用原 run 的剩余预算，不重置；停机时间是否计总时限在 manifest 固定，首版默认绝对 UTC expiry 计入停机时间，活动进程内仍用单调时钟计时。

SQLite 中损坏事务/页通过完整性检查拒绝 resume；JSONL 导出尾部不完整可从数据库重建，外部导入则只读已验证前缀并显式报 partial，不静默跳过损坏事件继续写。重复同 ID/相同内容幂等处理；同 ID 异内容拒绝。无跨任意外部系统 exactly-once 承诺。

### 4.3 一个受控后端：Docker/Linux

选本地 Docker Engine 执行 Linux 容器，暂不引入 OpenHands SDK。理由：当前工具是直接 subprocess，先实现少量 create/execute/cancel/destroy 能力，验证边界较小；避免同时承担 SDK 版本和同步接口迁移。计划撰写时本机尚不可运行 Docker；该历史观察已由 H3 在 Docker Desktop `desktop-linux` / WSL2 上的实测证据取代。

每 run 独立容器及 workspace，只挂载允许工作目录，不挂 Docker socket/宿主 home/凭据；非 privileged，固定镜像 digest、用户、CPU/RAM/pids、输出/artifact 配额，默认 network=none。容器文件和命令工具均经后端，不能只把 run_command 放进容器而保留可任意读宿主的文件工具。网络 opt-in 只声称所配置能力，不能把“有网络”误称域名 allowlist。资源/磁盘限制不可用就启动拒绝，不静默忽略。

run 终止时停止/销毁整个会话容器并核对无遗留进程；工具超时若无法可靠仅清该进程树，就终止会话并报告，不能复用可能污染的容器。grader 使用独立工作目录/会话，接收候选 patch 和只在验证侧挂载的数据。宿主本地后端仅 trusted_local 开发用途，其 filesystem_isolation/network_control/resource_limits 为 false。

| 平台/能力 | 本轮已核实 | 计划支持与验收限制 |
|---|---|---|
| Windows 宿主 + Python | Anaconda Python 3.13.9 可用；包要求 >=3.11；异步插件缺失 | 开发、schema、mock、SQLite、报告测试；当前 31 项 skipped 不是通过 |
| Linux + Python 3.11/3.12 | 本轮未运行 | 以 3.12 为首个执行环境，3.11 为最低兼容验证目标；安装时固定依赖版本 |
| Docker/Linux | H0 当日 PATH 无 docker、`wsl --status` 退出 1；该历史观察后来由 Docker Desktop `desktop-linux` / WSL2 验收取代 | H3 已在明确主机上完成真实隔离/资源/清理验收，见 `evidence/H3/README.md`；其他平台仍不作保证 |
| Windows 原生命令执行 | 当前 shell/argv 存在，但无进程树清理 | 保留 legacy/trusted_local；受控运行默认拒绝要求树清理的 profile。若之后选择正式支持，单独实现 Job Object（防派生竞态）并通过子孙进程测试 |
| OpenHands、macOS、远程执行 | 未验证 | 首版不纳入支持声明，不自行把其他机器作为执行目标 |

模型后端继续保留 OpenAI-compatible chat 的现有边界，不切换模型家族、不宣称所有兼容 provider 都支持同一 stream/usage 字段。默认离线 fixture provider；真实 provider/model/snapshot、计费单位、stream 能力在预算确定后按实际官方协议复核。无 usage 返回 unknown；无 streaming 明确走 non_streaming，TTFT 留空。

### 4.4 插件连接

首选进程内 **async Python Protocol + 版本化 JSON DTO**；两仓不互相 import 内部类，用本仓 no-op/fixture 单测先跑。插件只返回候选上下文、状态、度量和 action proposal，所有工具/LLM 请求由宿主处理，不把 LLM client、Shell 或 EventStore 对象直接交给它。进程内插件属于受信代码，接口隔离不能冒充恶意 Python 插件安全沙箱。

coding-agent 当前同步 WorkspaceAdapter 是已交接的边界信息，本轮未重新审计对方代码。主集成建议它新增 async adapter，将纯策略状态序列化；不可在已有 loop 内 `asyncio.run`，也不把阻塞 execute 塞主 loop。若必须保留同步 graph，再另定受控子进程 JSONL bridge，不先实现两套传输。不允许共享 runtime 预算之外的直连模型开销。

## 5. 阶段、依赖和可验收交付

以下 H0–H6 指总目标第 7 节的阶段；需求章节中的 H1–H7 是能力编号，不混用。总共七阶段。

| 阶段 | 前置与范围 | 独立交付/通过标准 |
|---|---|---|
| H0 现场基线与计划（本轮） | 读取目标、源码、AGENTS；不实施 | 原文 hash 一致；差距可定位；环境/skip 如实记录；四任务包可交接 |
| H1 执行正确性 | H0；HP-01 → HP-02 → HP-03 | 严格参数、真实本地流、共享 attempt 用量、deadline/取消及输出边界；离线故障测试通过。Windows 无清理保证时拒绝受控执行，Linux 清理验收单列 |
| H2 会话恢复 | H1；HP-04，文件写入核对及基本 artifact | 四崩溃窗口、不重复副作用、unknown、排他恢复、replay=0 外部动作；断言均有事件和 fixture 证据；原始观察不随 masking 丢失 |
| H3 受控后端与独立评测 | H1 执行接口、H2 事件；Docker 资源到位 | 真实后端 create/limits/cancel/destroy 通过；TaskEnvelope/EvaluationSpec 物理分开；独立测试计数/身份可信；删测/零测/伪造输出不通过；全分母 manifest/results/report |
| H4 窗口与策略接口 | H1 网关/预算、H2 原日志；接口可先于 H3 集成 | none/masking/summary/mask-then-summary 四合法视图，溢出前拒绝；摘要来源与成本；no-op/fixture 插件、状态恢复、requested/actually_injected、major/minor 兼容测试。首版先交接口+none/masking |
| H5 最小真实证据及联调 | H3，H4 基础；付费预算到位才真实调用；RepoSkill 就绪才联调 | 至少一个真实模型+固定 repo 修复由独立 grader 验证；三故障/机制 case study；跨仓一次真实连接，兼容版本与降级明确。有限配对实验另冻结协议，允许负结果 |
| H6 按需增强 | 核心已稳定，用户选定价值 | 薄 API/连续任务/额外并发或官方基准各自提案，不作为前面完成前置 |

推荐执行顺序：HP-01（完整测试依赖+参数边界）→ HP-02（真实流）→ HP-03（在途取消/有界执行）→ HP-04（恢复）→ H3 → H4 基础 → 单任务真实证据。H4 接口 DTO 的本地准备、grader fixture 可独立推进，但不得多实现者同时编辑 loop/factory/schema。未定 Docker 主机不会阻塞 HP-01/02、HP-03 的 mock 验收、HP-04 SQLite fixture。

## 6. 首个可投递版本：R1

R1 是本计划中的里程碑名，不是已发版号。目标为 H1–H3 + H4 的接口/none/masking + 至少一个真实端到端修复任务。四策略全面实验和多任务 RepoSkill 联调可后补；本次已完成一次受控跨仓联调，不要求先证明正向跑分。该目标已在 2026-09-21 按声明范围完成，逐项证据见 [R1 收口记录](R1-CLOSEOUT.zh-CN.md)。

R1 必须同时具备：

1. 不需要 key 的故障 demo：非法/断流工具不执行，在途取消后无后续写；输出有上限，环境探针只有允许变量。
2. 恢复 demo：写后崩溃进入核对/unknown，不能重复追加；四窗口测试及 replay/resume 分别有证据。
3. 一个真实 Docker/Linux 后端通过隔离、资源与销毁验收；没有它只能称“离线预览”，不能标 R1 受控执行完成。
4. 一个公开 issue+固定 repo 的真实模型修复任务，独立 grader 报告采集/通过/回归、测试篡改与 patch；若首任务失败，应诚实作为失败证据，继续在批准预算内寻找可演示修复，不能造成功记录。
5. manifest/events/artifacts/run-result/evaluation-result/report 完整可关联；报告能离线重生成；声明区分 verified/unverified/contradicted。
6. README 支持矩阵、运行预算说明、架构/恢复说明，以及超时清理、写后崩溃、上下文机制（含负结果可）三篇短案例。

R1 产物目录采用 `runs/<run_id>/` 的同等布局：`manifest.json`、`events.sqlite3`、`events.jsonl`（导出）、`artifacts/`、`run-result.json`、`evaluation-result.json`、`report.md`。private grader 数据放运行目录之外、从不挂入 agent 会话。H3/H5 CLI 已以 `--help` 和实际运行核实；各阶段证据目录保留过程失败，不覆盖原始事实。

## 7. 验证要求与后续证据纪律

HP-01 首先在专用 Python >=3.11 环境补齐 dev 依赖，确认 `pytest-asyncio` 可用；不修改 conftest 把跳过伪装通过。新高风险测试必须真实运行，结果同时报告 passed/failed/skipped 和不支持的平台。现有 regression 通过不能替代新故障用例。

H3 grader 的测试信号必须来自验证侧固定 runner：命令由 EvaluationSpec 控制，隔离 pytest 配置/插件注入，测试集合有固定 hash/身份。独立 workspace 应从 base+候选代码 patch 构建，记录对测试/配置的修改；零采集、依赖缺失、收集失败、runner 被遮蔽均不可 pass。只有打印“all tests passed”不能成为证据；空断言列表不能真空通过。agent 终止不等于成功，未知验证为 unverified，不强称欺骗。

环境失败计入 assigned task 分母并单列；旧 degenerate 指标只作 legacy/条件分析。恢复/重跑生成 attempt 关系，不能覆盖旧失败。成本包括重试、子任务、摘要、插件 controller、grader；离线构建单列且有预先约定摊销。未知 tokens/cost 用 null+来源，不填 0。

性能先用本地 fixture 做 1/5/10 并发，记录 CPU/RAM、资源 profile、失败数、取消收敛、p50/p95 与样本量；50 并发可选。模型对照不在本轮跑：先冻结任务/仓库/base hash、variant、repeat、模型与采样、窗口、工具、资源、预算和完整分母，再选两个策略做 smoke。正式实验开始时按 research-workflow 形成独立版本化合同；这里未把候选任务数当已冻结实验协议。

## 8. 真正待定项与无需等待的工作

| 待定项 | 在何处成为前置 | 当前处理 |
|---|---|---|
| 首批由 Codex 还是 Cursor 实现 | 用户启动实施时 | 同一任务包，用户选实现者；本轮不自行启动 |
| 专用 Python 3.12 环境与 dev 依赖 | H1 完整 async 验收 | 本轮不安装；HP-01 中完成，记录版本/依赖 lock 或 freeze |
| Docker 可用主机、镜像、CPU/RAM/磁盘 | H3 真实集成；HP-03 Linux 实测 | 不自动安装 Docker/WSL，不连接其他机器；先做离线接口/fixture |
| Windows 进程树是否成为正式支持承诺 | 若要受控 Windows 原生执行 | 默认不承诺；需要则新增专门任务及真实进程树验收 |
| 真实 provider/model 和总费用上限 | H5 真实调用 | 单列模型调用数、tokens、货币/币种上限；key 存在不代表费用授权 |
| schema 兼容/诊断协议细化 | 首次跨仓联调 | 见契约提案，先用 v0.1 语义本地 fixture；不改变公共原文 |
| 对方插件可用版本 | H5 RepoSkill 联调 | 单仓 no-op/fixture 不等待对方；不擅自安装或改其仓库 |

预算估算采用 `任务数 × variant数 × repeat数 × 每 run 硬调用上限`，另列每调用输入/输出 token 上界及价格版本；summary/controller/重试包含在 run 预算，离线 memory 构建和 grader另有总账。价格或 usage 不可得就报告未知，不做虚假精确估算。

每包结束由实现者交 diff、行为证据、实际命令输出、剩余风险；若由 Cursor 完成，后续 review 读取真实代码与产物，不仅凭其摘要。先保存本轮文档供用户选择实施方式，等明确启动某阶段后连续完成该阶段已授权的常规工作。
