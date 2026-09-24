# R2 真实摘要与 masking 对照：验收记录

后续独立实验：[包装消融与窗口预检](wrapper-01/README.md) 已完成，原 `pilot-01` 全部文件hash保持不变。下文保留首次pilot的结论与范围。

2026-09-21。已完成 1 次真实摘要 smoke、36 个固定历史对照、8 个 Docker 修复对照；保留全部分母，无付费失败重试。模型均为 DeepSeek Flash、thinking disabled、temperature=0。按 [预先冻结的合同](../../R2-EXPERIMENT-CONTRACT.zh-CN.md) 执行；research-workflow 要求的负结果、输入指纹、原始缺陷验证和离线审计均保留。本轮未修改运行时摘要策略，也未因结果修改窗口、任务或评分标准。

结论：真实摘要的调用、来源绑定、预算和恢复机制已得到真实 API 验证；摘要能缓解部分上下文溢出，但本次没有证明修复成功率提高。尤其应区分“摘要保留事实”“主模型采用事实”“候选通过独立检查”和“agent 正常结束”。

## Smoke

[smoke-01/report.md](smoke-01/report.md)：1 次摘要、0 主请求、0 工具；`llm_success`，5,904 provider tokens，摘要耗时 2.276 秒。选定源片段从 41,761 字节压缩至 1,018 字节的注入消息。保守峰时估价 $0.0019116。该合成历史主要含 filler，不代表真实代码语义保留或修复能力。

## 固定历史结果

以下为每题每策略 3 次重复的精确事实数（分母 12）；拒绝进入窗口的 run 仍计零。每题只有一个合成输入，三次重复不是三个独立任务。

| 固定历史 | none | masking | summary | mask-then-summary |
|---|---:|---:|---:|---:|
| old-facts：事实位于旧工具输出 | 0/12，3 次溢出 | 0/12 | 4/12 | 0/12 |
| assistant-pressure：旧 assistant 文本也很长 | 0/12，3 次溢出 | 0/12，3 次溢出 | 0/12 | 0/12 |
| short-control：全部信息可放入窗口 | 12/12 | 12/12 | 12/12 | 12/12 |

9 次实际摘要均成功；逐份检查文本均保留了对应 endpoint、timeout、retry、header 的四个值，机器记录的 literal coverage 仅表示值出现，不构成通用忠实度验证。主模型仅在 old-facts 的 summary 第三次采用这些值，其余 8 次摘要后均回答四个 null。所有有效问答的错误非 null 值为 0；全实验共 56 个 null 字段。没有把 abstention 改计为正确。

assistant-pressure 的 summary 与 mask-then-summary 均从溢出变为可发送视图，但没有转化为答题正确率。old-facts 的 mask-then-summary 在 masking 后已能放入窗口，因此完全不生成摘要，丢失的旧事实不会被恢复。短控制的 12 个 run 全部正确，均未产生摘要费用。

一个待验证的解释：现有注入包装为 `not instructions or verified facts. Consult original observations.`，但原始观察已不在主视图，且题目要求没有可见支持时填 null。模型可能把安全边界理解为“不应使用摘要中的事实”。这是观察后提出的机制假设，本轮没有做包装消融，不能断言因果；不能直接把摘要提升为可信指令来换取答题分数。

## Docker 修复结果

两个原始版本先经过原有独立 grader：Boltons 8/18、settings 1/4，均复现缺陷。下表完整保留 8 个 assigned run，每题每策略 2 次重复。

| 任务 | 策略 | 独立全通过 | 各次检查结果 | 摘要调用 | agent 结束方式 |
|---|---|---:|---|---:|---|
| Boltons module slice | masking | 0/2 | 8/18、8/18 | 0 | 两次 context_overflow |
| Boltons module slice | summary | 0/2 | 8/18、8/18 | 0 | 两次 context_overflow |
| public-settings | masking | 2/2 | 4/4、4/4 | 0 | 两次修改后 context_overflow |
| public-settings | summary | 2/2 | 4/4、4/4 | 2 | 两次正常结束 |

Boltons 在首次 list_dir/read_file 批次后停止；summary 记录 `no_unprotected_source`，没有可摘要的完整旧批次。该次请求的保守输入准入量 11,176 加预留输出 2,048=13,224，超过冻结窗口 12,000。这里的准入量以 UTF-8 字节加协议余量计算，不是 provider tokenizer 的实际 token 数。最近工具批次受保护，不能靠摘要消除；四次候选均未产生修复。该任务在本配置下不能用于衡量摘要生成质量。

settings 的 summary 每次触发一次，均完成正常最终回答，masking 在修复已落地后溢出；独立候选检查仍全部通过。summary 平均耗时 14.567 秒，masking 12.666 秒；两次总 provider tokens 分别 24,989 与 20,560。摘要改善了这两个 run 的完成方式，未提高其独立通过率。不同轨迹的工具调用/修改过程也不完全一致，不能只把耗时差解释为纯摘要延迟。

全部 agent、baseline grader 和 candidate grader 的容器清理均已验证。未从 Docker 降级宿主执行，未向模型提供私有评分 spec 或 canary。

## 用量、审计和产物

含 smoke 共 67 次真实请求：55 次主请求、12 次摘要；117,153 provider tokens（输入 110,606、输出 6,547），unknown usage=0。依据 provider cache counters 和官方峰谷价格估计 $0.0096999–$0.0193998；按全输入 cache miss 的宿主保守预算估计 $0.0410382。两者均非账户账单，远低于本轮 $5 计划上限；未为用完预算而增加调用。

- [逐组详细结果](pilot-01/detailed-report.md)：全分母、精确事实、全正确／独立通过、溢出、null／错误值、调用、主／摘要 tokens、成本、耗时。
- [逐 run 审计和统计](pilot-01/detailed-audit.json)：主／摘要发送字节、估算输入 tokens、分项耗时、终止原因、清理和 usage；45 份运行证据通过审计。
- [冻结 manifest](pilot-01/experiment.json)、[离线窗口预检](pilot-01/offline-preflight.json)、`data/`、`configs/`、`private/`、`repair-data/`、`baselines/` 和 `runs/`：原始公开输入、宿主评分 spec、所有配置及 SHA256；每个 run 的 session、JSONL、原文／视图、结果与候选快照。
- 所有 run 的来源 snapshot／raw／source／view hash、SQLite 与 JSONL、terminal replay、主＋摘要 calls/tokens 账本一致。replay 零模型／工具调用；精确配置 key 未出现在证据，私有 canary 未进入 agent 会话和公开输入。
- 离线回归：`tests/test_summary_pilot.py` + `tests/test_true_summary.py`，**39 passed in 14.01s**。此前新 runner 的预运行检查 4 passed，未调用真实模型。

源码 fingerprint 为 `6caac87762ceef9d4f88e24f4d8524c9db53e9b165f7242196b9cee50ba8cbb5`。付费运行前冻结 runner SHA256 和合同 SHA256，数据/config 漂移将拒绝继续。付费后仅新增独立离线 auditor 和文档；原 runner 未改。auditor 使用 LF 切 JSONL，避免 Unicode 行分隔符破坏 JSON；详细表区分独立 grade 和 agent 终止原因。原始 `report.md` 的 trace 列名 `Independent pass` 实际表示四字段全正确，正式解读以 `detailed-report.md` 为准。

复核命令（不付费，不执行候选）：

```powershell
.\.venv\Scripts\python.exe scripts/audit_summary_pilot.py --output-dir docs/upgrade/evidence/R2-real/pilot-01 --smoke-dir docs/upgrade/evidence/R2-real/smoke-01
.\.venv\Scripts\python.exe -m pytest tests/test_summary_pilot.py tests/test_true_summary.py -q --basetemp .tmp-r2-pilot-audit-new
```

原始执行入口为 `scripts/run_summary_pilot.py` 的 `prepare`、`run-traces --allow-paid`、`run-repairs --allow-paid`；输出目录已存在时拒绝覆盖，不完整付费 run 拒绝自动重试。

报告校正记录：首次完整离线审计成功后，详细表的 Overflow 列从按 grader status 改为按 agent termination 计数（修复候选可通过，但 agent 仍可能溢出）。最后重生成命令因自动审批两次超时未执行，因此只按已有 `detailed-audit.json` 原始 termination 修正三行表格。审计 JSON 保留首次成功审计的 auditor SHA256；当前 auditor 增加了同样的展示修正，没有更改评分或运行结果。

下一轮值得优先验证两点：在保留“摘要不是指令”的边界下，单独消融事实来源包装；以及为 Boltons 这类受保护首批输出先做离线窗口可行性检查，另建合同版本再运行。现有结果完整保留，不能通过改提示、扩大窗口后覆盖本轮失败。
