# 首批任务包 v1.0：Codex / Cursor 共用

2026-09-21 收口更新：HP-01/02/03/04 的实现与本地验收、H3/H4/H5 和一次跨仓联调均已完成；Linux 进程树和 Docker 证据见 [H3 验收](evidence/H3/README.md)，R1 总结见 [R1 收口记录](R1-CLOSEOUT.zh-CN.md)。以下“待启动”、入口不存在及旧环境缺失等表述均保留为 09-18 计划基线，不是当前完成状态。

日期：2026-09-18。状态：**历史交接基线，已封存**。当时任务尚未实施；当前完成状态不在本段重复改写，见上方更新和 [R1 收口记录](R1-CLOSEOUT.zh-CN.md)。总计划见 [IMPLEMENTATION-PLAN.md](IMPLEMENTATION-PLAN.md)。冻结源码为 `1f5903b620895ad8af3289ffeae529c15c3576a0`。

## 统一交接规则

将本文件及对应任务 ID 交给实现者即可，不需猜测“完善某模块”的含义。开始时必须读取本仓 `AGENTS.md`、总计划、三份目标及基线文件，确认当前 HEAD/diff。若 HEAD 已前进，按符号复核差距，不回退用户改动。`docs/changes/SOLID-D2-REMAINING-CLOSEOUT.zh-CN.md` 是用户已有修改，禁止覆盖。参考路径不可用应记录，不虚构已读。

只改本仓、该包允许范围；不发消息、不改对方仓库、不提交/推送、不跑付费模型、不大规模下载。每批同一组文件只交一个实现者；四包都涉及 loop，因此按顺序交接，不同时让两个执行者改它。包完成不代表后续包也完成，每包可依据自己的 fixture 和不变量单独验收。

现有基线、准确命令及环境前置见 [BASELINE-EVIDENCE.md](BASELINE-EVIDENCE.md)。本轮运行了完整现有套件，未额外重复跑每个选集。下文给出的新测试名是**计划新增的验收入口，尚不存在/尚未执行**；不能把它们写进“已通过”。已核实的旧文件可用同一 pytest 入口复验，新入口必须由实施者创建并实际运行后再报告。

统一命令 C0（已执行；见基线记录，沙箱外重跑结果 117 passed/31 skipped）：

```powershell
Set-Location D:\crq\src\coding-harness
$env:PATH='D:\crq\base\Anaconda3;D:\crq\base\Anaconda3\Scripts;' + $env:PATH
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONDONTWRITEBYTECODE='1'
& 'D:\crq\base\Anaconda3\python.exe' -m pytest tests -q -p no:cacheprovider --tb=short
```

实施验收必须改用具备完整 dev 依赖的项目专用 Python，记录绝对解释器路径；上面 Anaconda 缺 pytest-asyncio，仅是现场基线，不能用于新异步能力的完整放行。允许临时 fixture 目录，禁止把工作区根目录作为 pytest basetemp 或清理目标。

每包交付 `docs/upgrade/evidence/<包ID>/` 中的短报告：基线 HEAD、实际修改文件、测试命令和退出码、通过/跳过数、关键事件/输出、支持平台、未覆盖项、是否有模型调用（这四包应为 0）。fixture 只用假凭据；不得把真实 `.env`、Authorization 或用户代码全文写入公开证据。每包至少交一个能够在旧实现失败、新实现通过的行为反例，不只测试类是否存在。

## HP-01：严格工具参数与执行入口治理

**目标/动机**：模型给出的非法、越权或不完整调用必须在工具开始前被拒绝。修复 silent `{}`、非 object JSON、只过滤模型 schema 但未过滤执行的差距；为后面 stream、intent 和取消提供统一入口。

**当前证据**：`src/llm/client.py:219 LLMClient._parse_response` 捕获 JSONDecodeError 后设 `{}`；`src/tools/registry.py:28 schemas` 仅过滤发给模型的列表；`src/runtime/loop.py:176 AgentLoop.run` 直接对 arguments 添加 `_call_id` 后调用工具；工具参数没有本地统一校验。只读反例已确认非法 JSON 解析后变空对象。

**前置**：H0；无对方仓库、Docker 或真实 key 依赖。先建立/选择项目专用 Python >=3.11 环境，补齐 pyproject dev 依赖并记录 freeze/lock；不改变已有共享 conda 环境。若依赖安装受限，先完成实现与可运行测试，明确将完整异步验收标为未通过，不能删 skip guard 造绿。

**允许改动**：`src/llm/client.py`（仅非流式严格解析）、`src/tools/base.py`、`src/tools/registry.py`、`src/runtime/loop.py`（提取统一派发入口）、必要的 `src/config/schema.py` / `src/harness/factory.py`；新增 `src/tools/validation.py`、相关测试与包证据。现有工具 schema 可按真实输入约束修正；依赖声明允许添加一个明确版本范围的标准 JSON Schema validator，避免手写不完整通用验证器。

**排除**：真 SSE、进程实现、SQLite、Docker、摘要、具体策略、grader 重构；不改基础 prompt 语义。不把 schema 的默认值自动补进模型参数。

**输入/输出**：

- 输入 provider 完整调用 `{id, function:{name, arguments: JSON-string}}`；参数字节上限建议默认 64 KiB，可配置。先检查原始字节数再解析，必须为 object；保留大小写和原值，不强制转换类型。
- 完整 JSON 校验注册 schema 的 required/type/enum/长度及工具约束（run_command 的 command/argv 互斥）。本地通道不接受模型自带 `_call_id` 等保留字段；宿主 metadata 放 ToolContext，不混入被校验参数。
- 顺序为完成性/JSON/object/schema → enabled 工具与 policy → 派发。解析/校验错误携带结构化错误 kind、调用 ID 和安全摘要，不记录原始可疑 secrets；工具调用数为 0。未知/未启用工具分别报告，不 fall through。
- ToolResult 在保留 legacy success 适配的同时新增清晰 status 映射；注册声明 read_only/idempotent_write/non_idempotent。未声明写工具按 non_idempotent 保守处理，禁止默认重试自由 shell。

**行为验收（六项）**：

1. 输入 `arguments="{"`、`"null"`、`"[]"` 或缺 function/id 时均有可解释拒绝，spy 工具执行 0 次；不得转换成 `{}` 或归入成功 final。
2. 缺 required、类型错误、超 64 KiB、非法工具名、模型注入 `_call_id` 均不执行；错误种类/路径可区分。
3. 工具已注册但不在 enabled_tools 中时执行被阻止；即使 fake provider 不遵守发给它的 schema 也成立。
4. 有效 read/write 调用输出和 tool_call/result 配对与原功能兼容；宿主 ID 不会污染参数/trace 中的原始请求。
5. 同一模型响应中存在非法调用时，采用整批校验再派发：该响应的所有工具都不执行，记录 offending ID，避免前半批产生副作用后才发现后半批格式坏。
6. 新测试在完整 pytest-asyncio 环境真实执行，旧模型/工具/策略测试无未解释回归。正常命令退出非零不被误归为参数校验错误。

**已核实命令/验证入口**：C0；现场运行的只读参数反例见基线 P1。`tests/test_llm_client.py`、`tests/test_tools.py`、`tests/test_agent_loop.py`、`tests/test_policy.py`、`tests/test_command.py` 均存在并被 C0 收集。新增计划命令 `python -m pytest tests/test_tool_validation.py -q` 尚未验证，实施后须跑，并对旧失败/新通过保存输出。

**交付物**：严格解析器、校验/派发入口、工具分类与 status 兼容映射、依赖记录、`tests/test_tool_validation.py`、包证据。旧配置默认行为的有意收紧要列出迁移说明。

**风险/退出条件**：现有某些工具 schema 不完整，需显式修复其约束而不是宽松绕过；不要错误把 runtime-only 字段当模型字段。缺依赖只阻塞放行，不允许声称完整测试通过。若需改变共享 status 含义，先新增 CONTRACT-CHANGE，不偷改 v0.1。

## HP-02：真实增量模型网关与 client 生命周期

**目标/动机**：stream 的首 chunk 必须来自真实传输，交错 tool 参数可正确还原，中断不能执行部分调用；同 run 复用并关闭连接。

**当前证据**：`src/llm/client.py:136 chat` 每次新建 httpx client；`:186 stream_chat` 等完整 chat；`src/runtime/loop.py:133 _call_llm` 覆盖文本、每 delta append tool、EOF 无 done 校验；`src/runtime/retry.py:29 should_retry` 已有 429/5xx 规则，应保留。

**前置**：HP-01 参数边界及完整测试环境。无真实 API/Docker 依赖。先核对选定 OpenAI-compatible provider 的实际传输文档；本包本地 fixture 不根据未核实 SDK 自动切换模型或 API。

**允许改动**：`src/llm/client.py`、`src/runtime/loop.py` 的模型收集路径、`src/runtime/retry.py`、`src/harness/factory.py` 及脚本中的 client 关闭生命周期、必要配置；新增 `src/llm/stream.py`、本地 stream fixture 和测试。只改通用 gateway，不升级 provider/model。

**排除**：进程取消实现、持久恢复、插件、真实付费调用；不能继续把 chat 结果切片伪装 SSE。

**输入/输出**：

- 输入有界 SSE 字节流，允许行跨网络 chunk、空行/注释、多个工具 index 交错、ID/name/arguments 分段、finish_reason 与 usage 尾帧。parser 按实际 provider profile 定义终止条件，不把任何 EOF 当完成。
- 输出增量观察事件 + **一次**完整且已通过 HP-01 校验的 LLMResponse；tool 参数按 index 聚合并关联稳定 ID，不能只用尚未出现的 ID 作 key。
- client 可注入 httpx transport/client；明确 owning/borrowed 生命周期，`aclose`/async context manager 幂等；每 run 有界连接池，借用 client 不被误关。
- 每次调用/重试都记录 attempt、error kind、elapsed、usage provenance；本包先供内存 sink，HP-04 后统一持久化。缺 usage 标 unknown，不造 0，缺真实 stream 不生成 TTFT。

**行为验收（六项）**：

1. 本地受控 HTTP 服务在测试释放后续数据前，消费者已收到首 content chunk；用同步信号证明增量而非脆弱睡眠阈值，并保存 first_chunk/complete 的单调时间。
2. 两个交错 tool call，ID/名称/JSON 跨帧拆分后只执行各一次；文本多个 delta 完整拼接；最终 usage 被保留。
3. 缺终止标记、非法 UTF/JSON 事件、参数溢出、网络中途断开均标 incomplete/parse/network；即使部分 tool JSON 已闭合也不提前执行，工具 spy 总数为 0。
4. 取消 asyncio task 能关闭活跃响应和自有 client；正常/错误/重试都不泄漏连接。多个 chat 在一个 run 中复用 client，run 结束释放。
5. 非流式路径独立且命名诚实；provider 无 streaming 时 capability 与报告明确 non_streaming。旧 stream skeleton 测试应替换成真实行为测试，不能只改预期事件名。
6. 400/schema 错误不自动重试，429/暂时 5xx 可限次重试；失败 attempt 不遗失，重试前丢弃未完成聚合，所有工具只能在成功完成的 attempt 后执行。部分 usage 缺失保持 unknown。

**已核实命令/验证入口**：C0；`scripts/run_single.py --help`、`scripts/run_eval.py --help` 已运行（未加载模型任务）；旧 `tests/test_llm_client.py`、`tests/test_compact.py` 中 stream 测试被 C0 收集。新增计划命令 `python -m pytest tests/test_llm_streaming.py -q` 尚不存在/未验证；至少一个 test 必须跑实际 loopback HTTP 流，不能全部用直接返回对象的 mock。

**交付物**：真实传输/聚合器、生命周期 API、显式 capability、用量来源记录、`tests/test_llm_streaming.py` 与 loopback fixture、包证据。报告分别说明本地验证与未做 provider 集成。

**风险/退出条件**：兼容 provider 格式不一致；profile 不支持就拒绝/降级而非猜测。若本机禁止 loopback，保留 parser 测试并报告集成 unavailable，不能把 transport mock 当完整传输验收。整体 deadline 在 HP-03 接入，本包只验直接取消和单请求超时，不能宣称全局预算已完成。

## HP-03：在途取消、deadline 与有界工具执行

**目标/动机**：取消和预算耗尽必须作用于当前工作；命令不再因超时遗留子孙进程或先收集无界输出。分清已完成、失败、取消、超时、blocked 和 unknown。

**当前证据**：`AgentLoop._check_cancelled` 只检查边界并丢统计；`Budget.start_step/check_step_timeout` 不包围 await；`RunCommandTool.execute` 的 wait_for 只取消 communicate，未清理 proc；空 whitelist 返回 None；结果截断发生在解码全部输出后。

**前置**：HP-01、HP-02；Linux 实测需可用 Linux 环境，若尚未到位仍可独立交付 Windows mock/能力拒绝部分，但“进程树已清理”验收不能放行。

**允许改动**：`src/policy/budget.py`、`src/runtime/loop.py`、`src/runtime/retry.py`、`src/tools/command.py`、ToolContext/ToolResult、配置/factory；新增最小 `src/execution/base.py`、`src/execution/local.py` 和输出收集器。可修改 subagent 接入共享 deadline/账本；若本包不完成子预算，受控 profile 必须拒绝启用 subagent，legacy 路径明确标注。

**排除**：Docker 后端本体（H3）、Windows Job Object 正式支持、恢复数据库、通用调度系统。

**输入/输出**：

- 输入 validated request + operation_id/attempt_id + cancel signal + 有效 deadline=`min(run, step, tool/request)`。重试退避受相同 deadline，取消后不再启动下一工具/attempt。
- 共享预算同时对 model call/attempt 数、token 上限和可选货币上限做预留/结算：调用前为输入估算与最大输出预留，调用后优先用 provider usage 结算；失败/中断若 usage 未知，保留保守预留并标 unknown，不能当免费后无限重试。有货币硬限但无可信价格表时拒绝付费启动；额外 controller/子模型也必须登记，不能只累计最终成功响应。
- 输出结构化 status、exit_code、truncated、bytes_seen/kept、cleanup_state 和 error kind。即使 failed，stderr/部分 stdout 仍能通过安全观察表示，避免现有 to_message 丢失有用输出。
- stdout/stderr 并行边读边限量；建议初值每路内存 64 KiB、单工具 artifact 1 MiB、单 run 16 MiB，manifest 固定。达到 run 输出上限后取消生产者并清理，不无限丢弃；落盘上限也必须 enforce。
- 环境为空白名单时只保留声明的最小启动变量（如 PATH/Windows 必要系统变量）；不默认继承 HOME/USERPROFILE 等敏感路径。无显式允许变量就不可见，假凭据探针不接触真实 secrets。
- Linux trusted_local 用新 process session/group + TERM→短宽限→KILL→wait；对子孙脱离 process group 无法保证时 capability 不得称完整隔离，强保证由 H3 会话容器销毁完成。Windows 不支持树回收则受控 profile 在创建进程前 blocked/unavailable。

**行为验收（六项）**：

1. 正在 HTTP 流、重试退避、慢工具时触发取消，当前任务被取消、关闭/回收后结束；同响应后续写工具不启动。最终结果保留此前步骤/usage/失败计数。
2. run deadline 短于 step/tool 时以 run 为准；超时终止原因区分于用户取消。离线测试 cleanup 收敛目标 2 秒（另记 cleanup 宽限）；超出预算必须显式 cleanup_failed/unknown，不伪报已停。另用本地模型计数 fixture 验证超过 call/token/货币预留额度时下一次请求数为 0，失败 attempt 不释放为“已知零成本”。
3. Linux fixture 派生子孙进程，每 100ms 写临时 marker；父取消/超时并完成回收后观察 3 秒 marker 不增长、进程不可存活。测试自身 finally 兜底清理；组外逃逸只在容器测试，不在用户宿主制造失控进程。
4. 并发 stdout/stderr 各输出至少 20 MiB，内存持有和 artifact 大小不超过声明 cap，峰值采样/读缓冲计数有证据；没有全量 communicate 路径；截断信息和退出状态不会被截没。
5. 注入假环境值后空白名单和只允许一个变量两组结果准确；禁止变量不出现在子进程观察/trace，取消错误日志也不得泄密。
6. 不支持平台/后端在进程创建前报 unavailable/blocked，不能自动转宿主；正常退出非零、超时、用户取消、policy 拒绝和无法确认副作用的结果分别映射。

**已核实命令/验证入口**：C0 覆盖现有 `tests/test_timeout.py`、`tests/test_command.py`、`tests/test_agent_loop.py`；基线 P1 环境函数探针已运行。新计划命令 `python -m pytest tests/test_cancellation.py tests/test_execution_limits.py -q` 尚未验证；Linux marker/process-tree 测试需记录平台/解释器及实际命令，Windows skip 不能算通过。

**交付物**：统一 deadline/cancel 控制、清理与输出限量器、能力 profile、env 语义迁移说明、两个新故障测试文件、包证据与支持矩阵。

**风险/退出条件**：asyncio cancellation 本身不会杀 OS 进程，必须 finally 回收；shell/argv 均不能遗漏。取消需要清理宽限，不能承诺所有副作用回滚。若 Linux 不可用，交付清楚标“部分完成/待平台验证”，不得声称 HP-03 全验收，更不在本包顺便安装 WSL/Docker。

## HP-04：单写者事件、状态重建与保守恢复

**目标/动机**：将可丢失/截断的事后 trace 提升为恢复事实来源；实现最小单机 session，不重复不可确定写副作用。

**当前证据**：`src/tracing/events.py EventBus` 只有 timestamp+payload/flush；`TraceLogger` 以秒命名；`src/runtime/state.py AgentState` 只有内存 phase/history；`AgentLoop.run` 每次从空消息初始化。没有稳定 operation/attempt、intent、reducer、checkpoint 或 resume/replay。

**前置**：HP-01 的工具类别/入口，HP-03 的取消/终止模型。本包的 SQLite/reducer fixture 可先独立实现，真正 loop 恢复须接上前置；不得双写临时事件协议后宣称公共契约已完成。

**允许改动**：新增 `src/tracing/store.py`、`src/tracing/artifacts.py`、`src/runtime/session.py`、`src/runtime/recovery.py`、必要 `src/contracts/` 公共 DTO；修改 events/logger/state/loop/factory 和局部受控文件写以支持 hash 核对。新增故障测试、CLI 最小 replay/resume 接线（若新脚本命名，完成后验证 help），不改旧数据。

**排除**：分布式 store/锁、跨机器恢复、任意外部系统 exactly-once、特定 Memory 算法、真实模型实验、自动迁移旧日志为可信恢复记录。

**输入/输出**：

- RunEvent 保留共享 v0.1 字段语义：schema_version/event_id/run_id/task_id/seq/time/step/parent/operation/attempt/tool_call_id/event_type/payload或artifact。候选事件由宿主分配 ID/seq，只有一个写者。
- SQLite 本地事务持久化，JSONL 作为导出；intent 提交前不得执行。纯 reducer 产出消息/操作状态、预算累计、插件 opaque state、最后 seq，checkpoint 只是派生缓存。
- 文件替换可用已记录 before/after hash 和原子写核对；append/free shell 为 non_idempotent，写后未记结果就 outcome_unknown，不自动重放。intent 存在但无结果时也不能根据“不见 started”推断没发生。
- resume 校验代码/config/schema/backend/workspace/artifact/绝对 expiry；不匹配拒绝并给理由。replay 不接可执行工具；已终止 run 不因重新调用而重执行。

**行为验收（六项）**：

1. 四个崩溃窗口使用受控子进程/故障注入分别验收；每次恢复检查同一逻辑写的调用计数、文件内容 hash 和事件关系。无结果的非幂等 append 保持 unknown，永不重复追加。
2. result 提交而 checkpoint 过期时只重建，不重执行；replay 对全部轨迹的执行器 spy 调用为 0，输出可与在线最终 state 对比。
3. 两个进程同时 resume 同 run 时只有一个获得排他权，另一个明确拒绝；不会 lease 到期后未终止旧 worker 就启动新 worker。
4. 重复同 ID/同内容幂等，异内容冲突拒绝；SQLite 损坏拒绝写恢复；JSONL 尾部坏行显式 partial/重导出；不静默删除中间事件。
5. 缺 artifact、workspace 被换、未知 schema major、配置/backend 不兼容时给具体拒绝理由；schema minor 扩展按契约白名单兼容，Oracle 字段不能以未知字段绕入公开输入。
6. masking 前原始消息/工具观察已保存；日志/输出配额有效；恢复预算包含前 attempts 和停机策略，状态序列化不泄密、不重置预算。

**已核实命令/验证入口**：C0 包含 `tests/test_compact.py` 的旧 EventBus 测试和 loop 测试；基线中的 `rg`/源码位置可核对。新计划命令 `python -m pytest tests/test_event_store.py tests/test_recovery.py -q` 尚未验证。真实恢复测试必须至少一次跨进程退出再加载同数据库，不能仅 mock 一个异常就声称崩溃可恢复。

**交付物**：事务事件存储、artifact 引用、纯 reducer/checkpoint、排他恢复与兼容校验、四窗口 fixtures、replay/resume 命令或 API 行为说明、两个新测试文件与包证据。

**风险/退出条件**：日志提交与外部写无法全局事务，unknown 是合法终止结果，不应当作要偷偷重试的 bug。旧 JSONL 可保留只读报告适配，不能凭截断 StepRecord 恢复。若需要破坏性公共字段变更，在本包交 CONTRACT-CHANGE 后待同步，不改对方文件。

## 下一批候选（本轮不作为首批实现包）

H3 的 Docker 生命周期、独立 grader/完整分母与 H4 的 context/plugin 应在四包交付后按实际接口重新细化。不能把这四包单独完成称为 R1；真实后端、验证方隔离和至少一个真实任务仍是首个可投递版本的必要证据。
