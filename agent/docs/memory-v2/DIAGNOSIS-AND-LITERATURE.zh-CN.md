摘自 2026-10-13 的方案调研，原文件未公开

## 1. 诊断：A5 为什么是零

### 1.1 和交接说明的出入

| 说法 | 交接说明 | 文件或复算 | 处理 |
| --- | --- | --- | --- |
| 同题重试的花费 | 约 212 次、约 70 元（按 0.33 元/次） | B0 失败运行平均 0.538 元、33.1 次调用（本会话复算，53 次）。重试的都是失败过的难题，按 0.33 元估会偏低约 40% | 本文按 0.54 元/次估 |
| 有失败的题数 | "53 次失败运行" | 53 次分布在 22 道题上（13 道 0/3 共 39 次，9 道中间档共 14 次） | 功效按 22 道题算，不是 53 |
| 其余数字 | B0 115/168、B2−B0 −1.8pp [−8.3, +4.8]、9/51、5/153、0 次、70 张卡 | 与 RESULTS、CASE-DATA、FINAL-REPORT 一致 | 无 |

另外，FINAL-REPORT 第 7 节注明 CASE-DATA 文首写"引用第 7 节"而正文只有第 1–4 节；我读到的 CASE-DATA 文首写的是"引用本文件第 1–4 节"，已经一致。

### 1.2 本会话复算的几个数（描述性）

| 量 | 值 | 来源 |
| --- | --- | --- |
| B0 r1–r3 失败运行的修改位置 | 53 次里 39 次改到了 gold 文件，11 次没有改任何非测试源码，3 次改在别的文件 | summary 的 `changed_files` 对比私有 patch 的 `+++ b/` 路径，测试文件按路径规则粗略去掉 |
| B0 r1–r3 解出运行的修改位置 | 115 次里 110 次改到了 gold 文件 | 同上 |
| 失败运行的停止原因 | 35 次用满 40 次调用，17 次自己提交，1 次解析错误 | summary `stop_reason` |
| 卡片的理论上限 | 56 道题里只有 11 道，存在任何一张"同仓库、更早、validated_fix、非本题"的卡片的非测试文件和 gold 文件有交集；实际检索命中 9 道 | v6 卡片 + main-targets 的 `created_at` + 私有 patch |
| 有失败的题再跑一次能否解出（"新鲜重试率"） | 0/3 档 13 道：B0 r4 和 B2 r1–r3 合计 2/52；中间档 9 道：20/36 | 用 r4 和 B2 当"不带同题信息的再试一次"，B2 带了跨题卡片，但第 1 节已说明卡片基本无影响 |
| 过程量的配对差标准差（56 题，B2−B0） | 调用次数 4.24（检出下限约 1.6 次）；花费 0.088 元（约 0.033 元）；首次编辑轮次 4.55（约 1.7 轮） | 每题各组平均后相减，下限按 2.8×s/√56 |
| 测试命令因环境报错（模块找不到、参数不认等）的运行 | 168 次里约 7%，集中在 pytest 仓库 | 正则粗筛 events 里的 `run_command` 输出，只能当量级 |
| 单次运行墙钟 | 中位 2.6 分钟，平均 3.0 分钟 | events 最后一条的 `elapsed_ms` |

### 1.3 三类原因的权重

**记忆内容（相关性、抽象层次）：权重最高，有数据直接支持。**

- 理论上限只有 11/56。也就是说，把 BM25 换成 embedding、RRF、重排，最多把命中从 9 道提到 11 道，而且这 11 道里 B0 大多是 3/3 或 0/3。检索改进在这个卡片池上没有空间。
- 卡片内容是规则提取的"改了哪些文件、中途自述"，对一个已经能定位的模型几乎是冗余信息：解出运行 110/115、失败运行 39/53 都已经改在了 gold 文件上。
- 抽象层次：A5 没有测过 LLM 提炼的策略，所以"抽象策略有没有用"在 A5 里是未检验的，不是被否定的。

**注入方式（被动塞入、位置、措辞）：权重无法从 A5 识别。**

- 153 次里 5 次打开卡片独有文件、0 次改在那里，调用次数 23.6 对 23.7。这说明 agent 不按卡片走。
- 但卡片多数本来就无关，agent 不理会无关信息是正确行为。真正指对的 9 道题全在天花板或地板上，没有一道能看出"指对了但没被采纳"。所以 A5 区分不了"注入方式不行"和"内容不值得采纳"。
- 反过来的证据：R2 包装实验里，措辞从"指令"改成"可能有误的历史证据"，采纳率从 7/27 到 26/27。措辞对采纳的影响是存在的，只是 A5 没有机会表现出来。

**评测设置（天花板、模型太强、任务类型）：权重高。**

- 34 道 3/3、13 道 0/3，能变化的只有 22 道（中间档只有 9 道）。
- 设计检出下限 13.1pp、数据下限 9.0pp；文献里 SWE-bench Verified 上的跨任务记忆收益是 3–5pp（第 2 节）。A5 的规模本来就测不出文献量级的效应。区间上限 +4.8pp 能排除的，也正好是文献量级的上沿。
- 失败的形态：35/53 次用满调用预算，39/53 次改在 gold 文件里但改错了细节。这类失败需要的是"这个改法已经被测试否定过"之类的同题信息，跨题卡片给不了。

**小结：** 主因是内容和任务的错配（跨 issue 相关性低 + 瓶颈在修复细节），次因是天花板和样本量。注入方式未被检验。这直接决定了方案排序：先做"内容 100% 相关"的同题重试，用它顺带检验注入方式；跨题记忆只在任务同质的环境（agentic-rl）里再试。

## 2. 文献里的设置和数字

只列我实际从论文正文或摘要里读到的数字。arxiv 的 HTML 页面是用 curl 拉下来再本地抽文本读的；github 页面没能打开。

| 工作 | 任务和设置 | 报告的数字 | 和本项目的关系 |
| --- | --- | --- | --- |
| ReasoningBank（Ouyang 等，arXiv 2509.25140，ICLR 2026） | SWE-Bench-Verified，mini-SWE-agent（只有 bash 的 ReAct 循环）；记忆由 LLM 从成功和失败轨迹提炼成策略；正误标签由 LLM-as-a-judge 给出，**不看 ground truth**；测试时边做边积累 | Table 2：Gemini-2.5-flash 无记忆 34.2%（30.3 步），Synapse 35.4%，ReasoningBank 38.8%（27.5 步）；Gemini-2.5-pro 无记忆 54.0%（21.1 步），Synapse 53.4%，ReasoningBank 57.4%（19.8 步）。WebArena 上最多 34.2% 相对提升 | SWE 上跨任务记忆收益约 +3.4 到 +4.6pp，强模型更小。Synapse（存原始轨迹，最接近 A5 卡片）在 pro 上是 −0.6pp。是否在全部 500 题上评测、重复次数、置信区间：未核实 |
| SWE-Exp（Chen 等，arXiv 2507.23361） | SWE-bench Verified，MCTS 类框架加 Instructor/Assistant 双角色；多层经验库（理解层、修改层），成功和失败都存；**检索时排除同仓库经验以防泄漏** | v1 正文：DeepSeek-V3-0324 下 41.6% Pass@1；不用经验 37.8%；用 2/3/4 条经验分别 40.4%、40.2%、39.6%；消融去掉理解经验 38.4%，去掉修改经验 39.0%。摘要（较新版本）报 Claude 4 Sonnet 73.0%，对应的无经验基线未核实 | 跨仓库经验 +3.8pp。正文 6.2 节写到：早期让 Instructor 显式引用经验，导致过度依赖、在已有足够信息后仍套用不合适的策略，后来改成只作为消息上下文。这和 R2 包装实验的发现方向一致。重复次数和区间未核实 |
| Agent KB（arXiv 2507.06229） | SWE-bench **Lite**，OpenHands，最大 50/100 次迭代；知识库来自其他框架的轨迹；"Agent KB ✓"配置**只对第一轮失败的题做第二次尝试** | Table 2：GPT-4o 50 次迭代 16.33→20.33（pass@1），100 次 26.00→29.67；GPT-4.1 24.33→28.33，28.67→31.67；pass@2/pass@3 更高（GPT-4o 50 次 29.33、31.33）。正文说 Claude-3.7 在 50 次迭代下 30.00%→51.00%，对应的是 pass@1 还是 ✓ 配置未核实 | 跨任务 pass@1 约 +3 到 +4pp；大幅提升来自"失败后重试"的 pass@k 设置，相当于把同题重试和知识库混在一起。这恰好说明同题重试是收益大头，也说明报告时必须把重试和记忆分开 |
| Agent Workflow Memory（Wang 等，arXiv 2409.07429） | WebArena（GPT-4，在线模式：边做测试题边归纳 workflow）、Mind2Web | WebArena 总成功率 35.5%，BrowserGym ax-tree 基线 15.0%；摘要报 WebArena 相对提升 51.1%、Mind2Web 24.6% | 收益大的前提是同网站流程反复出现。SWE 跨 issue 不满足 |
| Dynamic Cheatsheet（Suzgun 等，arXiv 2504.07952） | 测试时按序做题，模型自己维护一份"小抄"；AIME、GPQA、Game of 24、Math Equation Solver | GPT-4o 在 Game of 24 上 10%→99%（发现并复用 Python 暴力解）；Claude 3.5 Sonnet AIME 2024 +27%、AIME 2025 +30%；GPQA-Diamond +9%，MMLU-Pro 工程和物理 +8%。这些是百分点还是相对值：未核实 | 同质任务、存在一个可复用解法时收益极大。对应 agentic-rl 的 6 类 bug，不对应 SWE |
| Reflexion（Shinn 等，NeurIPS 2023，arXiv 2303.11366） | 同一题多次尝试，失败后模型写反思，放进下一次的上下文 | 摘要：HumanEval pass@1 91%，同期 GPT-4 80%。ALFWorld、HotpotQA 的具体数字：未核实 | 同题重试的原型。HumanEval 的设置里模型可以自己生成测试，和我们"只给 1 比特"的设定不同 |
| ExpeL（Zhao 等，arXiv 2308.10144） | 从训练任务的成败轨迹提炼自然语言 insight，测试时召回 insight 和相似轨迹 | 只读到摘要，摘要没有数字。HotpotQA、ALFWorld、WebShop 的具体结果：未核实 | 跨任务 insight 的代表，依赖任务同质 |

从这张表能读出三点：

1. 在 SWE-bench 上，跨任务记忆的 pass@1 收益集中在 +3 到 +5pp。A5 的 56 题设计检不出这个量级。要检出 4pp，按 A5 的 s≈0.35 需要约 (2.8×0.35/0.04)² ≈ 600 道题，比 SWE-bench Verified 的 500 道还多。**所以在 SWE 上再做一次跨题记忆实验，预期又是零，这一点在开跑前就能算出来。**
2. 收益大的设定（DC 的 Game of 24、AWM 的 WebArena、Agent KB 的 ✓ 重试）要么任务高度同质，要么是同题重试。
3. 这些工作都没有报告按题配对的置信区间或预注册（就我读到的部分而言，未全文核实）。这正是本项目方法论可以拿出来讲的差异。

## 7. 读过的文件、查过的文献、未核实的说法

**读过的文件**

- `D:\crq\src\coding-agent\docs\memory-v2\HANDOFF-BRIEF.zh-CN.md`
- `D:\crq\src\coding-harness\docs\PROJECT-HISTORY.zh-CN.md`
- `D:\crq\src\coding-agent\docs\A5-FINAL-REPORT.zh-CN.md`
- `D:\crq\src\coding-harness\docs\sprint\A5-CASE-DATA.md`
- `D:\crq\src\coding-harness\docs\sprint\A5-MAIN-DESIGN.zh-CN.md`
- `D:\crq\src\coding-harness\docs\sprint\A5-MAIN-INVENTORY.md`（第 1–4 节）
- `D:\crq\src\coding-harness\docs\sprint\A5-MAIN-FREEZE.md`（只检索了注入和预测相关段落，没有通读）
- `D:\crq\src\coding-agent\docs\sprint\A5-MAIN-RESULTS.zh-CN.md`
- `D:\crq\src\coding-agent\reposkill_agent\memory\card_plugin.py`
- 一份本机个人笔记（未公开）
- agentic-rl：`docs/plan/PROGRESS.md`（部分）、`HELDOUT-PREREG.zh-CN.md`（前半）、`CHECKPOINT-1C.md`、`PHASE-2C-PROMPT.zh-CN.md`（检索数字）
- 只读扫描：`coding-harness/runs/a5-main/*/b*/r*/summary.json` 和 `events.jsonl`、`runs/sprint5-main-private/*.json` 的 patch 路径、`configs/sprint/main-targets.yaml`、`coding-agent/benchmarks/a5/memory-cards-v6.jsonl`。复算脚本放在系统临时目录，没有写进任何仓库。

**查过的文献**：ReasoningBank（2509.25140v1 正文）、SWE-Exp（2507.23361v1 正文和 Semantic Scholar 摘要）、Agent KB（2507.06229v4 正文）、Agent Workflow Memory（2409.07429v1 正文）、Dynamic Cheatsheet（2504.07952 正文）、Reflexion（2303.11366 摘要）、ExpeL（2308.10144 摘要）。

**没有核实的说法**

- 同题摘要在 SWE-bench Verified、强模型、1 比特反馈下的效应大小：没有找到直接可比的文献数字。A6-R 的"预期有效"只有 A5 数据上的机制依据。
- ReasoningBank 在 SWE-Bench-Verified 上的题数、重复次数和区间；SWE-Exp 73.0%（Claude 4 Sonnet）对应的无经验基线；Agent KB 中 Claude-3.7 30.00%→51.00% 属于哪种配置；Dynamic Cheatsheet 的 +27%、+9% 是百分点还是相对值；Reflexion 在 ALFWorld、HotpotQA 上的数字；ExpeL 的全部数字。
- 第 1.2 节所有"本会话复算"的数字：测试文件的判定、环境报错的正则都是粗筛，没有由执行侧复核。
- 方案 C 的 GPU 时间、方案 D 中小模型对小抄的反应：都是估计，没有实测。
- A 的功效来自模拟，假设效应在每次失败运行上是同一个加性提升，真实情况可能集中在少数题上，功效会更低。
