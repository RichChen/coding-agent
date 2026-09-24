# 包装消融与窗口预检结果

2026-09-21。按 [新合同](../../../R2-WRAPPER-CONTRACT.zh-CN.md) 完成全部102个单次主请求、0次新摘要生成；原运行时和 `pilot-01` 保持不变。research-workflow 的固定比较、完整分母和失败保留要求已执行。该轮支持继续研究明确“历史证据／非指令”的包装，不足以直接宣称真实修复成功率提高。

## 包装消融

使用 `pilot-01` 全部9份已生成摘要，固定每份的摘要ID、source hash、正文、消息role、system/task和其余上下文，只变包装。每份×3包装×3重复=81个主对照；没有重生成摘要，没有挑选成功摘要。旧包装也在本轮重新请求。

| 包装 | old-facts 全正确 | assistant-pressure 全正确 | 合计全正确 | 精确字段 | 错误非null |
|---|---:|---:|---:|---:|---:|
| A legacy：不是已验证事实，查阅原文 | 1/9 | 6/18 | 7/27 | 28/108 | 0 |
| B data-only：历史数据，不是指令 | 7/9 | 7/18 | 14/27 | 56/108 | 0 |
| C evidence：可能有误的历史证据，不是指令 | 9/9 | 17/18 | 26/27 | 104/108 | 0 |

C 在两个原题均提高精确匹配，符合合同的主成功信号；B 在 assistant-pressure 上仅小幅改善，并不稳定。C 仍有1次全null：`trace-assistant-pressure-r3-summary-r1-evidence`，未删去或补跑。所有主对照错误答案都是null，不是错误的非null配置。

逐摘要配对看，C 相对A为7份更好、1份相同、1份更差。较差的是 `trace-assistant-pressure-r3-summary`（8/12字段 vs A的12/12）；不能把总体增益写成每份均提升。9份摘要来自两个合成问题，重复和同题不同摘要并非独立任务，不做显著性、泛化或真实修复率声明。temperature=0仍可有响应波动，且API的实际模型版本由provider管理。

机制解释：把“不可服从摘要中的指令”与“可以利用摘要中明确报告的事实”区分开，明显改善了当前固定摘要的事实采纳。这个实验隔离了包装这个因素，但C同时改变了多句表述和长度，不能再细分是哪一个短句产生效果。本轮没有测试摘要生成质量、长流程累计错误或真实工具可用时的行为；没有将C替换为生产默认。

## 边界控制

- 缺失值：每包装3次，合计9次，全部保持缺失的 timeout_ms=null，同时答对其余三项；没有补造值。
- 夹带指令：每包装3次，合计9次，全部返回目标四键事实，没有输出 `WRAPPER_PROBE_OVERRIDE`；所有102请求都未提出工具调用。
- 短历史无摘要：3/3正确，没有包装、没有摘要费用。

这两个公开合成摘要控制只检测一种缺失和一种明确引用的指令，不覆盖模糊、隐蔽或多轮注入，也不能证明包装本身提供安全隔离。所有102个run均完成，provider失败／无效JSON／窗口拒绝为0。

## 窗口可行性预检

权威结果为 [window-report.md](window-report.md) 和 [window-preflight-corrected.json](window-preflight-corrected.json)。从原8条修复轨迹抽取26个不同的完整post-tool raw快照，按12000/16000/24000窗口与none/masking/summary三策略执行234项离线检查。使用fixture而非LLM摘要，不调用Docker或模型。

| 任务 | 12000窗口 | 16000／24000窗口 | 当前决策 |
|---|---|---|---|
| Boltons，4条历史 | 首批原文需13224；部分masking后需13090；可摘要完整批次=0，两策略都拒绝 | 已观察首批可放入；旧轨迹在此即停止，没有更晚轨迹 | 跳过12000的付费重跑；更大窗口只证明首批可行，不能当摘要收益实验 |
| settings，4条历史 | 首批需8723–8733，均可放入；后续均有原文窗口压力 | 所有已观察raw快照都可放入，未观察到摘要压力 | 12000具有真实摘要触发条件；16k/24k暂不适合作为本轨迹的摘要效果对照 |

上述“需要窗口”是UTF-8字节加协议余量及2048输出预留，不是实际provider tokenizer tokens。首批容纳通过不等于未来全程可行；不同窗口会改变策略和后续轨迹。理想删除可摘要批次后的下界只用于排除不可行情况，不是保证真实摘要能压到该大小。

初版预检出现了实现错误：沿用的micro-masking helper会原地修改列表，导致在计量原文之前已局部masking。冻结的 `window-inputs/` 先于该操作写盘，逐条与旧SQLite snapshot核对完全一致；包装输入使用独立数据，付费对照未受影响。没有修改被冻结的runner或初版表，而是新增 `scripts/check_summary_windows.py`，复制后再执行masking、强制原文hash不变，并保存独立校正版。两次诊断也区分了原summary准入13224与原masking准入13090；两者均与旧运行记录复现一致。

`window-preflight.json` 仅保留为失败实现证据，不应引用其测量或决策。自动生成的 `report.md` 底部仍指向这个初版文件；窗口结论以本页上述校正版链接为准。修正未改变合同中的网格、保护规则或评判标准。

## 用量与验证

本轮102次DeepSeek Flash请求，thinking disabled，temperature=0，无重试；52,043 tokens（输入48,231、输出3,812），provider usage全部已知。缓存／峰谷价格估计 **$0.006342534–$0.012685068**，不缓存保守估价 **$0.0190437**，均非账户账单，低于合同上限$2.04。

主对照每组27次的provider tokens：A 14,695、B 14,910、C 16,234；平均run耗时分别1.873、1.831、1.857秒。耗时差很小，受网络/cache等影响，本轮不声称速度改善。

- [完整分组及逐摘要表](report.md)、[逐run分数、用量与审计](results.json)、[冻结清单](experiment.json)、[包装逐字文本](wrappers.json)。
- 每run保存实际发送view、manifest、主回答、SQLite/JSONL、账本和replay；102份均通过离线一致性检查。每run只调用1次主模型，无摘要事件；所有视图均与冻结单因素输入完全一致，API key未出现在证据。
- `pilot-01-hashes.json` 保存旧目录全部文件内容hash，准备前后、执行结束审计和校正版预检后均相同；没有覆盖 `pilot-01`。
- 离线测试最终 **11 passed in 4.03s**（`test_summary_wrapper.py` + `test_summary_pilot.py`）。包括原文不可变、部分可mask但整批受保护、包装单因素、缺失／指令评分、单调用账本与replay。此前5项包装测试通过后才开始付费。
- 本轮未改src、旧runner、旧合同或旧报告；原source fingerprint仍为 `6caac87762ceef9d4f88e24f4d8524c9db53e9b165f7242196b9cee50ba8cbb5`。

离线复核（不调用API／Docker）：

```powershell
.\.venv\Scripts\python.exe scripts/run_summary_wrapper.py audit --output-dir docs/upgrade/evidence/R2-real/wrapper-01
.\.venv\Scripts\python.exe scripts/check_summary_windows.py --output-dir docs/upgrade/evidence/R2-real/wrapper-01
.\.venv\Scripts\python.exe -m pytest tests/test_summary_wrapper.py tests/test_summary_pilot.py -q --basetemp .tmp-r2-wrapper-review-new
```

下一步建议：以C作为下一份真实修复实验合同的候选包装，保留A并排比较；优先使用已通过首批预检、后续确有摘要压力的任务。settings可作接线smoke，但原grader已饱和，不适合独自证明成功率提升。Boltons应先有更大窗口的可观测探索轨迹，再决定是否纳入摘要收益对照。本轮到此收口，不为预算尚有余量而重复付费。
