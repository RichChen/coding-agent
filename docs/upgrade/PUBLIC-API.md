# 首批公开策略 API v1（本仓接口，非已冻结跨仓 wire 协议）

2026-09-21 A5 补充：H4/H5 真实单任务联调及受控注册已由另一仓完成，下文早期“待联调”是历史状态。新增 `reposkill_agent.experiments` 离线 API，未修改 H4 签名：

- `ExperimentContract / DatasetManifest / MemoryBuildManifest`：冻结 E-A1、来源/开发暴露审查、同池索引和结构化记录；`require_frozen` 拒绝 hash 或 profile 漂移。
- `select_variant(task, evidence, facts, contract, dataset, memory, variant, now=..., decision_id=...)`：纯本地 B0–B3 决策，返回逐候选拒绝原因和 `context_candidates()`，没有执行器。
- `audit_injections(decision, receipts, usage, run_id=...)`：实际注入需要候选 hash/片段、host evidence ref、修复模型 operation/attempt；prepared view 不等于实际注入，observed_following 保持 unknown。输入 host 证据须来自可信采集器，引用字符串本身不证明远端内容真实性。
- `summarize(contract, dataset, memory, rows, build_dev_usage=...)`：同 profile 的首 run attempt、所有 assigned 分母、缺行/invalid_env/degraded、paired task differences 和全部已提供模型调用成本。`model_attempts_started` 必填；缺 usage 要保留 unknown attempt；重跑另行保留并计费；构建调用绑定 memory_id；dev 成本单列，缺结果行时完整费用为 null。宿主仍需保证完整提供 run/attempt inventory。
- `estimate_cost(contract, price=None, ...)`：仅容量/价格公式，不运行实验。模型、价目、真实 heldout 清单和费用上限未绑定；machine/human 成本不默认为零。

从已保存 JSON 重建主指标：用相应 DTO 的 `model_validate_json` 读取 `experiment-contract.json`、`dataset-manifest.json`、`memory-build-manifest.json`，从 `results.json["rows"]` 验证 `ResultRow`，调用 `summarize`。本次 `usage.json` 为空；未来 build/dev attempts 也必须一起传入，不能丢掉额外调用。场景矩阵和注入计数分别由 `decisions.json`、逐条 host receipts 重建，不从修复结果反推。实际例子见 [A5 验收](A5-VERIFICATION.md)。

2026-09-19。下面的符号已实现；coding-harness 的实际插件签名、注入收据和 ArtifactRef ACL 仍按 CONTRACT-CHANGE.md 联调，不以本仓 schema 版本冒充两仓正式契约升级。

2026-09-21 更新：已按 H4 wire 0.1 实现数据型 async adapter，见 [H4-ADAPTER.md](H4-ADAPTER.md)。单仓合同已验证，真实跨仓运行、宿主持久注册及收据对齐仍待后续。

## 数据流和信任边界

20 题前置准备新增 `experiments.preparation.prepare_pilot20(source, lock_path, output)` 与 `scripts/prepare_a5_pilot20.py`：只读本地 pinned parquet、按公开列确定候选、导出公私分离材料及 240 assignments，输出永远 preparation_only。私有列不会进入 `PublicIssue` 或选择器，脚本没有模型/API/真实执行开关；实际宿主 grader 对接仍待完成，详见 [准备记录](A5-PILOT20-STATUS.md)。

预算授权后新增 `experiments.funding.prepare_funded_build(bundle, funding_file, output)` 与 `scripts/prepare_a5_funded_build.py`。它只把 20 个固定的历史来源转换为宿主 build jobs，并为每个来源预留一次 retry（共 40 个 attempts），校验目标/来源去重、私有评测材料隔离和 pilot/memory-build 分账；`execution_enabled=false`，不启动模型。实际运行仍只能由 harness 统一网关、预算和收据负责；MemoryRecord 只有在真实 public observation、验证 artifact、依赖映射和 operation/attempt 收据齐全后才能晋升。

`decode_public_task` → `EvidenceLocator.decide` → `render_public_context`，可通过 `plan_public_step` 一次装配并可选接 `select_memory`。这些函数不执行模型、shell、patch、测试或网络，不分配宿主 run-event 序号，也不恢复外部副作用。

PublicTask 与 EvaluationSpec 是分离类型。公开 DTO 默认 realistic；legacy TaskSpec/GraphRunner 仍 diagnostic。公开入口递归拒绝 oracle 字段，对未知 major 拒绝；较新 minor 的未知顶层扩展只记通用审计原因、绝不进入策略。已知嵌套结构仍严格校验。禁止字段包括 expected_files/tags/gold_patch/hidden_tests/category/future_trajectory。issue 原文的合法公开文件线索保留。

PublicTask 携带 repo identity/revision、workspace/profile 引用、公开复现和预算描述。task_id 只关联，不参与 lexical 排序/路径选择。family 当前只支持 code_repair。Private EvaluationSpec 与策略对象没有嵌套关系，真实部署必须保证 agent 工具实际不可读私有树。

`export_public_workspace(source,destination,task,manifest,evaluation)` 属于私有数据准备侧。manifest 必须 reviewed_public=true、匹配 repo revision，逐文件 hash 验证；只向新目录写入，拒绝覆盖、上下级目录、Windows 路径别名、目录遍历、symlink/junction 和私有文件引用。manifest 是可信人工/数据准备器的公开性声明，不是模型输入；任意源码中的答案/秘密不可能仅靠字段扫描全部识别，必须先审查公开文件集合。该函数不提供 OS 沙箱或抵抗并发目录替换的安全保证。

## 证据 API

`Observation` 包含 kind=file/search/public_test、path、start_line、content、repo_revision、ArtifactRef；body 必须与 artifact hash/字节数一致。host 负责解析引用的权限和观测真实性。`EvidenceState` 可 JSON 序列化，记录已读片段、proposal 累计配额、查询、假设和缺失项。

`EvidenceLocator.decide(task, tree, state=None, observations=())` 返回：

- needs_observation：有 read/search proposals，须由宿主检查执行后反馈；proposal_id 是本地相关键，不是宿主 operation_id。
- evidence_ready：已有相关公开代码，可形成 context，不表示已修复。
- insufficient_evidence：搜索后仍缺线索，无 oracle fallback。
- budget_exhausted：策略已用尽工具/文件建议配额；不代表宿主资源控制器。

首版支持公开文件引用、关键词/函数名与 host search observations，默认每轮 3 路径/累计 6 文件/12,000 字符/2,000 tree entries。没有训练检索器；不从 README 指令中生成 shell 操作。render_public_context 将公开只读测试正文纳入 snippets，而 writable_paths 排除 tests、test 目录和 test_*/*_test.py。最终写权限仍由宿主工具 policy 负责。

## 记忆记录与来源

`MemoryRecord` 保存稳定 ID/revision/supersedes、内容 hash、kind、status、来源 task/run/artifact/hash/代码版本、适用前提、依赖、公开验证及构建 usage。`BuildUsage` 区分无模型/provider/estimated/unknown，未知货币费用为 null。人工条目标 human-authored，规则抽取标 rule。

`SourcePolicy` 是可信实验配置：精确来源 allowlist、target IDs、截止时间、build/dev/heldout、排除 artifact hash/重复组/可选 repo 集合。gate 要求当前 task ID 在 target 排除清单中。`validate_build_manifest` 拒绝污染的源清单，即便污染条目尚未命中检索；无法推断的训练污染不做无污染保证。

`build_candidate` 只从内容 hash 已匹配、来源获准的 PublicTrajectory 结构化抽取，输出 candidate，绝不因轨迹自称成功自动 validated。`import_legacy` 读取副本/指定原文件但不改其字节；oracle、坏行和匹配秘密模式的内容只输出 hash/行号隔离审计。缺来源的合法条目保留 candidate/unknown，不能进入 realistic 注入。

## Store 与状态

`RecordStore` 使用独立 SQLite schema 1。旧 episodic_index DB 或未知版本拒绝。records/revisions 与 transitions 同事务；主键 (memory_id,revision)，同版本同内容幂等，异内容拒绝。每次 append 重新验证模型，不能利用 Pydantic model_copy 绕过 record 校验。快照 hash 覆盖排序后的当前记录；原始证据仅存 ref。

初始只能 candidate/quarantined；candidate → validated 需要公开验证及来源 policy；validated 可变 stale/conflicted/quarantined/retired；stale/conflicted 重验发布新 revision；quarantined → candidate 要显式 reviewed=true，仍需再次验证；retired 不恢复。语义或适用域修改不能复用原验证。状态不会被一次运行的失败自动永久删除。

store 只负责知识记录事务，既不替代 runtime event store，也不证明 host artifact 存储长期可靠。损坏新 store 的 schema/record 会 fail closed 报错；旧 JSONL 导入按行隔离。真实部署须用只读 snapshot、受控 resolver 和预先冻结的跨任务更新时机。

## Validity、gate 与收据

`check_validity(record, RepoFacts, now)` 是纯函数。已知 API 签名不等或包版本不满足 PEP 440 range → invalid；粗文件 hash 改变但语义不明、映射不全、缺失/冲突/旧版本 facts、过期验证 → unknown；必要条件都有一致证据才 valid。优先 invalid > unknown > valid。签名检查首版按给定规范字符串相等判定，是保守规则，不是自动语义兼容证明；RepoFacts 由宿主公开观察/可信提取器提供，本批没有全语言 API 自动提取器。

`DependencyIndex.affected` 只缩小重验候选，未知映射始终纳入；不替代 validity。commit 改变不单独失效所有记录，同 commit 下仍检查包环境。

`select_memory` 使用公开 issue 的 lexical 分数，依次检查来源、生命周期、validity、冲突、重复和字符配额，允许零条。没有存储记录就没有伪造 repo profile。输出 GateDecision，包含每条理由与 check evidence refs，以及待宿主注入的 context candidates。当前配额是完整序列化 hint 的字符数，不宣称 token 硬上限；实际 tokens/预算由宿主负责。

`confirm_injection` 只接受匹配 decision/candidate/request hash 的宿主收据，校验实际片段范围/hash 和 model operation/attempt；rejected 不能带内容，重复候选收据拒绝。缺 receipt 就没有 actually_injected；observed_following 默认 unknown，真/假判断另需可观察证据。收据真实性依赖宿主信任边界，不提供远程签名认证。

## 无标签 Skill 路由与策略 checkpoint

`route_public_skills(task, evidence, facts, skills, budget)` 是 realistic 专用入口。它只读取 `PublicTask`、已接纳的 `EvidenceState`、匹配 revision 的 `RepoFacts`、技能卡和显式 `PublicSkillBudget`；不会导入 `TaskSpec`、`TaskCategory`，也不会读取 `tags` 或 `expected_files`。输出版本化 `PublicSkillRoute`，分别列出 candidates、selected、rejected、原因和估算字符成本，允许零条 selected。技能所需前提若没有公开观察证据，直接拒绝；这只是词法 baseline，不执行技能或模型。

`PublicStrategyState`、`strategy_state_for`、`serialize_strategy_state` 和 `restore_strategy_state` 提供纯 JSON checkpoint。checkpoint 绑定 task hash、repo revision、evidence state、proposal IDs、memory snapshot ID 和 receipt cursor；恢复只做 schema/绑定校验，不执行读文件、工具、模型、注入或写回。

`run_public_rounds` 是单仓 fixture 的离线 walkthrough。每一轮由调用方传入 host 模拟的 observations，返回 proposals、context、memory decision 和 checkpoint；结果明确 `external_model_calls=0`、`tool_calls_executed=0`。它不属于 GraphRunner，也不实现 harness 的循环、事件、取消或恢复设施。

## 本批不提供

真实模型修复、独立 grader 执行器、隔离容器、取消/恢复、两仓 async plugin、warm 在线写回、生产 Secret DLP、未知仓库泛化结论。legacy L0/2/5 的 memory useful/stale 是注入后成败代理；原数值保留，新报告明确标记。新 demo 是 deterministic fixture，不写成真实模型实验。
