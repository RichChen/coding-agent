# R2 真实摘要与策略对照合同 v1

日期：2026-09-21；仓库 coding-harness。用户已明确授权真实摘要及后续 summary/masking 对照的付费使用。本合同在本轮首个付费调用前冻结；不更改 R1 / R2-lite 的历史结论。

## 问题、模型与费用

问题：在相同模型、原始历史和预算下，摘要能否保留 masking 丢弃的任务事实，或缓解 masking 无法处理的旧 assistant 文本溢出？代价是否值得？真实修复任务是否真的触发摘要、产生可观察差异？这是工程探索性 pilot，不声称论文新方法或基准修复率。

沿用已验收的 `deepseek-flash`，`thinking=disabled`，temperature=0，不启用插件、planner、subagent、Pro。2026-09-21 已重新读取 [官方价格](https://api-docs.deepseek.com/quick_start/pricing)：当前映射 DeepSeek-V4.1-Flash，美元/百万 tokens 峰时 hit=.006、miss=.30、output=1.20；非峰时半价。预算预留不依赖 cache，取输入 .0003/千、输出 .0012/千。实测 usage、cache 字段、unknown 与保守费用分开，非账户账单。

本轮先设美元上限 $5：单摘要 smoke ≤$0.10；固定轨迹对照 36 个 run × $0.05=$1.80；修复 pilot 8 个 run × $0.30=$2.40，合计硬 run 上限 $4.30，其余不自动花掉。失败和准备失败保留，不隐式重跑付费请求。API 调用串行；预算余量不代表必须用完。

## S：真实 smoke

使用已有 `scripts/demo_true_summary.py` 的公开合成历史，1 个真实摘要、0 主模型请求/工具。既有 512 输出 tokens、65536 输入字节、30 秒请求/60 秒总时限；不先调参。成功须 llm_success、provider usage、预算结算、原文/source hash 与 snapshot seq、JSONL/SQLite/replay 对应，且视图合法。失败也是结果；发现实现问题先保留证据、修复并离线验证，新的 smoke attempt 独立目录，不覆盖失败。

## T：固定轨迹配对对照

数据为本仓新增的三个明确标注的合成开发上下文，全部 facts 来自原始公开 tool observations；不是实际 agent 探索轨迹或 benchmark。在付费前生成并保存 raw/私有 answer spec/hash，offline fixture 验证窗口行为。无训练、无数据 split 搜索，无看结果后挑题。

- T1 `old-facts`：旧工具输出中有四项当前任务需要的事实，近期观察只提示未完成；长 observation 导致原文溢出而 masking 可放入窗口。
- T2 `assistant-pressure`：同样有四项事实，但旧 assistant navigation notes 较长；masking 仍溢出，summary/mask-then-summary 可以压缩完整旧批次。
- T3 `short-control`：短历史；所有策略都能放入窗口，不应收费摘要，用于检测不必要调用。

每题四策略 `none/masking/summary/mask-then-summary` × 3 repeats，共36个 run。每个 run 相同窗口8000、keep_recent=1、主输出512、摘要输出512；最多1次摘要+1次主模型 attempt，共享131072 token、$0.05和120秒 run预算；摘要30秒/累计60秒。summary failure=reject，不把失败回退混进正常方法组。主请求不提供 tools，只读历史后返回指定 JSON 的四个键；缺乏证据应填 null。私有 expected 值仅评分器持有，不注入 system/task/summary/provider。

主指标为全分母事实精确匹配数/总事实数；并列列出完整四项正确率。溢出/格式错/环境失败保留分母计零，同时单列原因；错误非null值与 null abstention 单列。次指标为窗口拒绝、摘要次数、发送字节/token估计、provider tokens、主/摘要费用、耗时、摘要事实覆盖。价格/usage未知不补零。按固定 seed=20260921 打乱每个 task-repeat 的四策略顺序；provider 不发 seed，不宣称完全确定性。

预期支持信号：T1 摘要保留更多旧事实；T2 减少窗口拒绝；T3 无额外摘要费用。独立失败信号：摘要幻觉/遗漏关键值；有效视图仍回答错；收益仅来自多花钱且同等输出无改善；mask-then-summary在T1不触发而与masking等价。所有这些均如实报告，不换指标。只做按题/重复配对描述，不把3 repeats当3个独立任务，不做显著性或普遍成功率声明。

## C：既有公开修复任务的探索性 pilot

复用已冻结 `boltons-475-strutils-slice` 和 H5-interop `public-settings-001` 的原始 public seed、public task 与 private EvaluationSpec，不读取修复候选作为输入；本次插件=noop。先由同一现有 IndependentGrader 验证原始版本确实失败。每题 masking/summary ×2 repeats=8 runs，顺序由同一固定seed配对打乱。

固定 Docker image digest/network=none/资源profile；窗口12000、keep_recent=1、主输出2048、工具输出4000字符；最多20步/24次模型attempt/200000累计tokens/$0.30/600秒，单步120秒；摘要最多2次、512输出tokens、131072摘要tokens、30秒单次/60秒累计，计入上述run预算。无自动重试。每次从相同原始seed创建新容器，独立grader在候选冻结和容器清理后执行。

主指标全分母独立 grader pass、通过/采集数；同时列 termination、摘要实际触发数、成本、发送量、工具次数、总耗时。结果与T分开。摘要未触发的run不能当摘要效果证据；两任务只允许机制/个案结论。若资源/执行环境不可用，先排查不花模型费，不从Docker降级宿主；保留invalid_env，不临时换题。此阶段不实现通用grader/H6。

## 产物与审计

每个run保存 public input、非secret config、源码与数据hash、manifest、SQLite/JSONL/artifacts、run result、摘要来源/版本/usage、独立结果。保存首次失败和完整assigned分母；重跑另有attempt关系。离线审计读取现有结果，不再次调用API；核对ledger calls等于main+summary、tokens来源、raw/view哈希、无凭据/私有spec泄漏、replay零外部调用、Docker清理状态。报告可离线重生成。

实施允许增加实验数据/窄runner/测试/报告，必要的 correctness 修复须标记前后版本；不因观察结果修改任务、窗口、预算或指标。用户这次已授权上述必要配置选择与付费实验，不重复征求每个run许可。若合同必须改变，先记录新版本及原因，按research-workflow要求向用户说明需要改变的评测项；旧结果仍保留。

AGENTS 指定参考路径再次检查不存在；沿本仓已有运行/预算/恢复接口实现。现有 H4/R2-lite 代码和已归档证据是工程基线；本轮不是文献新颖性研究，不重复开展无关文献调研。
