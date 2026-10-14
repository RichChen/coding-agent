# coding-agent 总修改目标 v1.0

日期：2026-09-18。目标仓库：`D:\crq\src\coding-agent`，Python 包：`reposkill_agent`。

对应 Codex 任务：[改造coding-agent](codex://threads/01a0b3a9-86da-7e71-900d-afe57a46cbd3)。

配套必读：[双项目协作与接口约定 v0.1](00_双项目协作与接口约定_v0.1.md)。收到本文件的首轮仅做理解、代码核对、文档和实施计划；用户后续决定 Codex 直接实施或 Cursor 承接，不立即修改产品源码或跑付费模型实验。

## 1. 一句话目标

把现有 RepoSkillAgent 从“在手工任务集上验证 skill/memory/router 的修复系统”，升级为**面向未知 issue、带可追溯与可失效记忆的 Coding Agent 策略和评测项目**，回答：在哪些条件下经验复用能帮助修复，什么时候应拒绝使用旧经验？

主工程底座由 coding-harness 提供；本项目负责定位、Skill、Memory、版本有效性、策略选择和公平对照。两个项目可独立展示，但技术深度应互补。它对应 Coding Agent、Agent Harness 算法应用、Agent Evaluation 等实习方向，不等同于基础模型训练或大规模 RL 研究经历。

## 2. 为什么这样改

### 2.1 招聘锚点

- [字节 Agent Harness 算法 A242905A](https://jobs.bytedance.com/campus/position/7677984300810438917/detail)：Context、Built-in Tools、Harness 与评测，需要可解释的策略、同底座对照和 grader，而非只列多 Agent 名称。
- [字节 Agent Infra 后端 A238339](https://jobs.bytedance.com/campus/position/7671205707161422133/detail)：Memory、轨迹、数据生产 workflow，为本项目的经验来源和治理提供工程落点；执行可靠性由 harness 承担。
- [字节 GUI Agent A148793A](https://jobs.bytedance.com/campus/position/7649303455514085637/detail)：轨迹质量、失败样本和 benchmark 是可迁移经验，但本项目先专注代码修复，不扩成 GUI 系统。

岗位调研主要确认了字节具体 JD，腾讯/阿里仍多为列表级线索，不能把它解释成已覆盖所有国内大厂。你学历与专业基本匹配，不代表已有技能足够通过算法面试；这个项目的目标是形成可核验的能力证据。

### 2.2 2026 年资料启发的具体问题

以下来自既有 2026-09-18 调研，当前文档不宣称重新复核或完成复现：

| 来源 | 借鉴点 | 在本项目的落地与限制 |
|---|---|---|
| [STAIR](https://arxiv.org/abs/2607.29658) | 从真实修复轨迹提炼分层程序性经验 | 由成功/失败过程生成有来源的经验，不只存人工标准答案；同仓库未来 issue 与跨仓库泛化分开 |
| [Invalidation Contracts](https://arxiv.org/abs/2609.00243) | 依赖变化后有针对性地失效经验 | 记录 API/文件/依赖版本和适用条件；原论文场景不是代码修复，这里是迁移假设 |
| [Measure Before You Manage](https://arxiv.org/abs/2608.31057) | 同 token 上限不保证管理成本公平 | 记忆构建、选择、验证和注入成本都入账，区分实际 usage 与估算 |
| [SERBench](https://arxiv.org/abs/2609.20050) | 按当前状态补缺失证据 | 以 issue、已读证据和公开测试反馈定位，替代 expected_files；检索指标不等于修复成功率 |
| [SWE-Skills-Bench](https://arxiv.org/abs/2603.15401) | Skill 并不必然有效 | 测无 skill、静态 skill、gating，并主动保留负迁移案例 |
| [Harness Design](https://arxiv.org/abs/2609.20804) | 同底座、单变量组件比较 | 新基线不能用不同调用预算或不同 context 能力偷换比较 |
| [OverclaimBench](https://arxiv.org/abs/2609.20812) | 最终声明需要轨迹证据 | “采用了记忆”“修复成功”都要有对应证据，而非仅从最终回答推断 |

本项目不以“复现这些论文全部方法”为目标，也不在没有相关工作核查和结果前声称提出新算法。

## 3. 现有项目如何保留

现有资产：固定 inspect→locate→patch→test→summarize 图，Manager/Locator/Developer/QA，SkillCard/domain gating，episodic/procedural/repo profile memory，router，context expansion，JSON repair，fake/OpenHands adapters 和消融设施。

历史主实验：48 个 synthetic medium tasks、4 个手工 Python 仓库、2 次 real DeepSeek repeat，L0=45.8%、L2=70.8%、L5=80.2%。保留原报告、配置与局限，不覆盖历史。它证明受控任务集中的正向信号，不能当成 SWE-bench 分数、未知仓库泛化、统计显著结论，或多 Agent 单独的因果收益。

此前审计发现，主路径很多角色是确定性逻辑，Developer 负责 LLM patch。`adapter="fake"` 与 `developer_mode="llm"` 可以同时存在，不能简单理解为整个实验是 mock；但也不能把这称为 OpenHands SDK 实际运行。

本次目录检查未发现可用 Git 仓库元数据。计划阶段说明后续如何记录基线：用户已有版本管理则接入；否则在开始实现时建立本地版本记录或限定范围的源码快照/hash manifest。不擅自对整个父目录 git init，不把 secrets、日志大文件和数据全量加入版本控制。

## 4. 当前入口与差距核对

| 当前模块 | 应核对的问题 | 改造方向 |
|---|---|---|
| `reposkill_agent/core/contracts.py`、`eval/task_spec.py` | task 对象是否混有 expected_files、gold、tags | 明确 PublicTask 和 EvaluationSpec，realistic 默认不可见 oracle |
| `agents/locator.py`、`core/context_expansion.py` | 是否依赖答案文件直接定位 | issue/检索/公开日志驱动的证据发现 |
| `eval/injection_policy.py`、`task_category.py` | category 是否来自人工 benchmark 标签 | 只基于运行中可观察信息路由，保留 oracle diagnostic |
| `memory/models.py`、`procedural.py`、`consolidator.py` | 经验是否缺来源、版本和验证记录 | 可追溯记忆、失效、冲突和隔离状态 |
| `skills/models.py`、`domain.py`、`retriever.py` | 是否通过任务标签选中“答案技能” | 可解释适用条件、成本、负迁移反馈 |
| `eval/llm_ablation.py`、`graph_runner.py` | L0/L2/L5 是否同时改动多机制/预算 | 冻结新协议，保留 legacy 复现实验 |
| `adapters/base.py`、`fake_adapter.py`、`openhands_adapter.py` | 主实验真正走什么执行 backend | 与 harness 集成并精确记录 adapter/backend |
| `llm/client.py`、`agents/llm_developer.py` | 构建/检索/repair 是否隐藏额外调用 | 统一成本记录，集成主路径走宿主模型网关 |

上述是审计线索，不是要求无条件重写这些文件。实施计划必须对照最新代码标记已满足/部分满足/缺失，并引用相关符号。

## 5. 最终使用体验与架构

用户输入公开 issue 和固定 repo 版本后，系统自己通过允许的工具探索代码，记录缺失证据，再在预算内选择是否使用 Skill/Memory，形成补丁并做公开验证。最终由独立 grader 验证，报告记忆来源、被拒绝原因、实际注入、任务结果及全成本。

```text
公开 issue + repo version + 已有观察
  -> EvidenceState / Locator
  -> Skill/Memory Candidates
  -> Validity + Domain + Budget Gating
  -> PolicyDecision（来源、理由、上下文候选）
  -> coding-harness（模型、工具、取消、事件、执行环境）
  -> 新观察 / patch / 公开测试
  -> 独立 grader + 逐任务对照分析

允许的已完成轨迹 -> 离线/受控 Memory Builder -> 版本化 MemoryStore
```

本项目可以先在现有 adapter 上独立开发策略和离线测试；不要等 harness 全部完成。最终主证据路径应至少有一次实际 harness 集成。现有 OpenHands adapter 保留为可选兼容，不为了简历再复制一套容器和生命周期管理。

## 6. 核心需求与验收

### A1 拆开 diagnostic 与 realistic 两条协议

- `diagnostic_oracle` 保留原 benchmark 的 expected_files、人工标签、脚本修复和 seeded conventions，用于机制排错，输出显著标记。
- `realistic` 是新的展示/主评测模式：只接收 issue、固定 repo、公开复现与工具观察。任务描述本来就出现的文件名可用，额外答案字段不可用。
- agent 可读数据结构、workspace、检索索引、trace 和 memory 构建源都不能泄露 gold/hidden tests。不能只从 prompt 删除字段却把完整 TaskSpec 传到 Locator。
- 隐藏测试由外部 grader 后置执行；测试结果写入公开记忆需遵守协议，不能利用 hidden grader 反复迭代答案。
- 同一次报告不能把两种模式的结果混成平均值。legacy 成绩附原协议说明。

验收：放入独特 oracle sentinel，检查序列化输入、prompt、检索文档、工具可见目录均不包含；改变 gold metadata 不应改变 realistic 策略行为；agent 能照常利用公开 issue 中的文件名。

### A2 从未知 issue 出发的证据发现

- 先用实用 baseline：issue 关键词、repo tree、ripgrep/符号检索、公开 traceback、imports/call sites；暂不训练 retriever，也不强制向量数据库。
- 维护 EvidenceState：当前假设、已读文件/代码范围、来源、公开测试反馈、尚缺证据、下一步探查理由。
- 文件选择必须可追溯到 issue 或观察，不允许通过 expected_files、任务 ID 映射、category cheat 或特制文件名查答案。
- 去重和预算优先，允许探索失败、证据不足或拒绝继续；不得“找不到就切 oracle”。
- 源码、注释、README 和旧记忆作为不可信任务数据，不因其中的指令就绕过策略或访问外部 secrets。

验收：任务不含 expected_files 仍能从公开线索定位；干扰文件和重命名不会触发硬编码；失败时报告已检查证据与限制。定位命中率若使用隐藏标签计算，仅由离线 evaluator 计算。

### A3 带 provenance 的 MemoryRecord

建议在现有 MemoryHint 基础上演化，至少保存：

- 稳定 memory_id、schema/version、类型：episode / procedure / repo profile。
- 来源 task/run/trajectory artifact、源 repo/base commit、时间、构建方式与模型。
- 适用域、前置条件、经验步骤、验证方式、预期失效条件。
- 涉及 API/符号/路径、依赖版本、可选文件或签名 fingerprint。
- 验证证据：允许的公开测试/日志、结果、验证时的代码版本。
- 状态：candidate、validated、stale、conflicted、quarantined、retired；缺失证据不能默认 validated。
- 构建成本、最后验证、使用/拒绝记录、可能重复来源和版本谱系。

避免在每条记录复制完整代码仓库；引用受控 artifact 即可。手工 Skill/Memory 合法，但要标 human-authored，不能称为自动学习。

验收：任一注入条目可追到来源和适用前提；来源缺失/内容损坏有行为；秘密内容能排除/脱敏；单条记录的版本变化可审计。

### A4 有效性与失效规则

- 检查结果至少区分 valid / invalid / unknown，并给出理由；相似度高不能覆盖 invalid。
- 首版采用可解释规则：API 签名变化、依赖版本不满足、来源文件/约束指纹变化、适用 repo 不符、验证过期。TTL 只能是一项弱条件，不是语义正确性的证明。
- 局部变化只失效相关经验；整库清空作为 baseline。没有可靠依赖映射时选择保守 unknown/revalidation，不能伪造精确失效。
- repo commit 改变不代表所有经验无效；应判断所依赖证据是否变更。反过来，commit 相同也不代表环境依赖没变。
- 对冲突经验排序/拒绝要可解释；重验用公开证据且计成本。quarantined 内容不能自动重新注入。
- 使用记录区分 retrieved、selected、actually_injected、observed_following；被注入不代表被模型采用，无法判断采用时标 unknown。

验收：API 改变后旧经验拒绝；无关文件变化仍可保留有效经验；缺版本信息走 unknown；冲突记录不同时作为强制指令注入；过时恶意经验不绕过 runtime 权限。

### A5 Skill 和 Router 收敛

- SkillCard 包含能力描述、输入/适用前提、操作建议、验证方式和证据；不要把 target patch 以“skill”名义直接塞入真实模式。
- Router 用 issue + EvidenceState + repo facts + budget 选择；保留规则/简单检索 baseline。引入 LLM router 必须作为独立、可计量的后续实验。
- 每次选择输出候选、分数/规则、接受/拒绝理由、预期与实际注入成本。
- 控制 top-k、总 context 配额、冲突和重复；允许选择零条，避免强制所有任务启用所有机制。
- 失败反馈不能简单“失败一次永久删除”，需要区分经验不适用、策略没采用、环境故障和实现错误。

验收：删除 benchmark tags 后仍可工作；所有拒绝/接受有理由；负迁移案例可重现；no-op 路由与无增强基线行为一致。

### A6 由轨迹形成经验

- 首版先支持结构化抽取：问题线索、定位证据、修复动作、公开验证、失败反例。可用规则/人工注释跑通，再按预算加入 LLM 抽象。
- 抽取必须基于允许的历史轨迹，不能读取目标任务 gold patch、未来测试答案或 held-out 目标已完成轨迹。
- 跨任务 memory 更新策略由实验协议固定。warm 模式记录构建任务、顺序、写入时机；cold 模式为每个 repeat/任务重置到声明的初态。
- candidate 经验先校验来源/结构/适用性，进入受控 store；不把模型自称成功直接晋升为 validated。
- 手工基准、真实仓库、同仓库历史经验分别标数据来源。跨 repo 重复 patch/代码要检查并报告，hash/相似性检查不能被称作完全消除训练污染。

验收：目标任务和未来数据加入构建 manifest 时被排除/拒绝；受控旧轨迹能产出来源完整的记录；构建成本可追踪。

### A7 与 harness 连接

- 实现 PolicyPlugin/adapter，参照共同 TaskEnvelope、事件、artifact、budget、result 语义。
- agent 提供策略状态的 serialize/restore，harness 决定事件顺序、持久化和恢复副作用。
- 现有 WorkspaceAdapter 是同步接口，而 harness 为异步；计划必须明确选 async 适配还是子进程 bridge，不在已有事件循环里嵌套 `asyncio.run`，不把阻塞操作塞进主 loop。
- legacy fake adapter 仍可跑离线 plumbing；实际报告记录 adapter、model backend、是否 mock，各维度独立。
- 如果 OpenHands 还没有实际集成成功，README 改成“提供可选 adapter，支持状态见矩阵”，不以其为主底座背书。

验收：harness 真实执行一个 RepoSkill 任务；日志能关联 memory selection、模型请求、工具、patch 和独立验证；关闭插件能做同底座比较；单仓 unit tests 不需要另一个仓库安装齐全。

## 7. 新的实验设计：先可信，再争取正收益

实验分三层，结果不可混用：离线 plumbing；可控机制/版本漂移任务；真实模型 + 固定仓库修复任务。旧 L0/L2/L5 仅按旧协议复现，新的主对比使用以下命名与控制变量。

### E-A1 记忆复用的公平 baseline

问题：同一运行底座和预算内，结构化经验比不使用记忆和简单文本检索更有价值吗？

| 组别 | 改动 | 固定项 |
|---|---|---|
| B0 无记忆 | no-op augmentation | 迭代 loop、工具、公开 context、模型、repair retry、预算一致 |
| B1 简单检索 | 从允许历史轨迹做关键词/BM25/简单文本检索 | 与 B2 使用同一历史来源池、候选与注入预算 |
| B2 结构化经验 | 对相同来源提炼 procedure/skill 并检索 | 抽象构建成本另记，线上总预算仍一致 |
| B3 结构化经验 + validity | B2 加有效性检查 | 单独量化拒绝、重验成本与结果 |

不能拿“一次模型调用 B0”比较“多轮探索 + 多次 repair B2”后宣称记忆提升。skill/router 的额外效应另做单变量 on/off，不在首轮做所有组合的指数级网格。

### E-A2 版本漂移下的记忆有效性（推荐的研究故事）

假设：API/依赖变化后，依赖级失效能减少已知过时经验的错误注入，并保留对未受影响任务有用的经验；是否提高任务成功率仍需独立检验。

四组：无记忆、静态记忆、检测到版本变化后整库清空、依赖级失效。使用相同基础修复策略、同一初始记忆库和变更集。A1 与 A2 分开跑，避免一轮实验混入多个问题。

漂移类型至少包含：相关 API 签名变更、依赖配置变更、无关文件变化；增加 unknown dependency 场景检验保守行为。人工构造漂移可用于机制测试，但要明确适用范围，不能因此宣称真实世界自动发现一切失效。

主指标分别报告：独立修复成功率、已标注 stale 记录的错误注入率。次指标：有效经验保留率、重验成本、错误经验可观察采用率/unknown 比例、任务耗时与全成本。

率的分母必须明确。例如 stale 注入率 = 注入的已知 stale 条目数 / 可评价的 stale 候选条目数，并同时给每任务“是否受到 stale 注入影响”的比例；不能用两个不同分母的率相减。有效性 ground truth 来自机制 fixture/离线标注，不给运行策略看答案。

支持信号：在固定协议下减少错误注入，较整库清空保留更多仍有效条目，且没有不可接受的成功率/成本退化。失败信号：误拒大量有效经验、规则只适配手工题、成本超过预算、记忆来源泄漏，或改进在同来源公平 baseline 下消失。

### 数据划分与成本规则

- 先冻结少量任务做 smoke（建议 3–5 个），不据此宣称能力提升。
- pilot 建议 12–20 个固定任务、3 次 repeat 的预算估算；正式规模由信号和预算决定，没有硬性全量 SWE-bench 目标。
- repo-disjoint 要按仓库划分，不能只随机切任务。仓库数量不足时不得声称跨仓库稳定泛化。
- 同仓库未来任务要遵守时间和代码版本；若时间信息不足，标合成时间/版本顺序实验。
- 记忆构建、调参开发、最终测试集合分开；held-out 结果不能反复用于修规则，需新版本协议和新 holdout。
- 同仓库未来 issue、未见 repo、不同 agent backend 是三种泛化，各自单列。
- model ID、采样配置、预算、context policy、环境、task list、失败计分方式、重复规则先冻结。模型服务不支持 seed 或不提供固定 snapshot 时写明限制。
- 全部外部模型调用计入：Developer、JSON repair、router、摘要、memory builder、verifier。公开报告线上成本及离线构建成本/预先约定摊销，不把构建免费化。

没有用户给出的真实模型调用预算时，先完成离线测试、实验配置和调用/token/货币上限估算，等用户选择费用边界再开跑。不能因 key 存在就默认无限授权。

### 分析与证据

输出逐任务结果、差异、失败类别和 trace 引用；对配对任务按任务/仓库聚类估计不确定性，避免将 repeat 当作新独立样本。样本少时报告描述性结果并承认无力判断显著性。

定位 recall、检索命中、已注入、模型采用、最终通过是不同层次；每个结论对应自己的指标。自动 judge 不应替代实际测试，LLM judge 的配置与成本单列。

负结果合法：例如结构化经验更贵而没有提升；失效正确但模型忽略了记忆；静态 skill 导致错误迁移。不要为了提升数字重新挑测试集或把失败样本去掉。

## 8. 阶段顺序与可投递版本

| 阶段 | 交付 | 通过条件 |
|---|---|---|
| A0 现状与协议 | 代码差距、历史证据边界、契约映射、任务包 | 保留现有成果，真实/诊断路径清楚 |
| A1 真实任务边界 | PublicTask/EvaluationSpec、oracle 隔离、基本 locator | 无答案字段可运行；泄漏 sentinel 验收通过 |
| A2 记忆可追溯 | MemoryRecord、来源、版本、状态、简单 retrieval | 每条注入可追溯，缺证据不误标已验证 |
| A3 有效性机制 | dependency check、unknown、冲突、重验、gating | 漂移/无关变化/冲突 fixture 通过 |
| A4 策略与集成 | 轨迹抽取、无标签 router、harness adapter | 一个跨仓端到端任务，统一预算/trace |
| A5 小规模实验 | B0/B1/B2/B3 或四组漂移对照，优先选一条 | 固定协议、逐任务结果、全成本和失败分析 |
| A6 可选增强 | 更多真实仓库、LLM router、跨 backend/分层经验 | 只有已有信号和时间/预算才扩展 |

首个可投递版本完成 A1–A3、可演示的公开 issue 修复和一组受控漂移证据即可开始投递；A4/A5 增强工程与研究说服力。不把所有可选实验视为必须先做完的门槛。

## 9. 最终产物与演示

- 更新 README：真实运行路径、支持矩阵、历史 vs 新证据、明确局限。
- 架构与代码阅读指南，能从 issue 输入追到 memory gate、model patch、验证结果。
- Memory/Skill schema、生命周期、来源和失效案例。
- offline demo：API 版本改动后旧经验拒绝，无关经验仍保留，unknown 可解释。
- online demo：公开 issue 的定位、修复、记忆选择和独立测试证据；费用有上限。
- 固定实验 contract、dataset/memory manifests、配置、完整原始结果和报告生成脚本。
- 至少三个案例：经验有用、经验失效/负迁移、baseline 更好或无差异。
- 面试说明：哪些角色是确定性逻辑、为何不用 benchmark tags、为什么 high similarity 不等于 valid、如何避免记忆污染、如何定义公平预算。

不得把“仓库中有 adapter 文件”作为集成成功证据。最终声明应指向具体配置、运行记录与结果。

## 10. 核心范围以外

不重做 runtime、Docker/网络隔离、分布式 worker、通用 FastAPI 平台、复杂 UI、向量数据库集群、RL 训练和全量官方 benchmark。向量检索、更多角色或自动记忆进化只有在简单 baseline 明确不足时才作为单独改动。

不为了营销把所有角色改成 LLM；保留确定性处理往往更容易测量、更便宜，也更容易解释。可以称为“结构化修复策略与记忆系统”，不必声称通用自主多智能体团队。

## 11. Codex / Cursor 实施要求

首轮按共享契约返回总计划，并重点给出 A1–A3 的 2–4 个小任务包。每包明确相关文件、当前行为、目标行为、不可泄漏数据、契约样例和验证命令；不要只写“完善 memory 模块”这种无法独立验收的指令。

建议 Codex 负责 oracle 隔离审计、baseline/数据 split 设计、失效语义与最终 review；Cursor 可承接接口已固定的 schema、局部迁移、报表、fixture 和 adapter 映射。工作交接时包含目标版本和已完成任务，避免双方同时重写同一模块。

用户后续授权开始后，按阶段完成实现与验证；但不得把“必须有正收益”作为编码目标。发现假设不成立时提交负结果和下一步选项，而不是偷偷改指标。

## 12. 依据和实施前检查

本地来源：`coding-agent与coding-harness项目审计与技术调研.md`、`2026年9月Agent业界学术更新与项目升级建议.md`、`国内大厂Agent日常实习岗位调研_2026-09-18.md`，位于协调任务的 outputs 目录。

正式实验前按 research-workflow 的合同形式固定假设、方法、基线、split、指标、seed/repeat、预算、失败信号和产物路径；目前文件中的规模是候选方案，不是已经跑过的结果。实验开始后变更协议需版本化并说明旧数据还能支持哪些结论。

现有实现优先复用，最新代码比旧审计更权威；发现修复已完成就记录，不重复改造。全程保留用户文件、旧结果和秘密配置边界。
