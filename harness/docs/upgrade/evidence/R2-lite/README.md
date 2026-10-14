# R2-lite 真摘要：实现与离线验收记录

2026-09-21。范围与任务包：[R2-lite 契约](../../R2-LITE-TRUE-SUMMARY.zh-CN.md)。本轮未调用真实 API、未运行 DeepSeek/Pro/思考模式、未启动 Docker 或通用判分/H6 工作。保留既有 R1 工作区和历史证据，未提交/推送。

最终源码、测试/脚本与 XML 的 SHA256 以及实际 Python 版本见 [final-source.json](final-source.json)。

## 交付与行为

| 文件 | 结果 |
| --- | --- |
| `src/runtime/summary.py` | async SummaryProvider、借用同一 LLMClient 的 adapter；固定 prompt、严格完整 JSON、禁止工具输出；独立摘要记录和共享预算结算 |
| `src/runtime/window.py` / `context.py`、schema / factory | 显式 fixture/llm；默认仍 fixture；仅策略溢出时调用；不递归使用已生成摘要；来源 hash 缓存；失败 masking/reject；原始历史不变 |
| `src/runtime/loop.py` / `recovery.py` | summary.started/settled 原子保存 manager state 与总账；raw snapshot → summary intent/result → context.prepared；恢复不重置次数；started-only/超预算/取消保守停止 |
| `src/llm/client.py` | chat 增加兼容的 keyword-only 输出限额/temperature 覆盖，不修改共享实例配置；缺失 finish_reason 保留 None，使摘要能够拒绝不完整结果 |
| `src/eval/h3_runner.py` / `runner.py`、`scripts/run_single.py` | context policy 进入 manifest；summary 单独进入 run result/trace/CLI；known summary tokens 也进入总 tokens；unknown 不伪装为实测零用量 |
| `tests/test_true_summary.py`、`tests/fixtures/summary_worker.py` | 34 个新增离线用例；含真正子进程退出与恢复、真实 adapter 的 MockTransport contract、完整单摘要 demo 的 MockTransport 路径 |
| `scripts/demo_true_summary.py` | 单条公开合成轨迹、最多一次摘要、无主模型请求/工具/grader；fixture 默认；真实路径需要显式模型、USD 上限、价格来源与 --allow-paid |

真实摘要作为不可信 user view，不能变成 system 指令、工具动作或插件 proposal。provider 只获得原始 system/task 约束与受控批次，不获得 EvaluationSpec、workspace executor 或插件对象。已有工具 policy 和私有 grader 边界继续有效。

## 实际测试

| 检查 | 结果 / 证据 |
| --- | --- |
| 首轮旧窗口/loop/client/budget 回归 | 34 passed |
| 新增离线测试第一轮 | 25 passed |
| 加入真实进程崩溃、完整 loop 取消后 | 29 passed |
| 全项目离线回归 | **347 passed、22 skipped**，72.10s；[offline-regression.xml](offline-regression.xml) |
| 最后补充恢复终止保护、完整 MockTransport demo 后的相关模块复验 | **89 passed、0 skipped**，42.48s；[summary-final.xml](summary-final.xml)，其中真摘要测试 34 项 |
| CLI help | `scripts/demo_true_summary.py --help` 成功 |
| 默认 fixture demo | [fixture-02/report.md](fixture-02/report.md)：视图 ready、模型调用 0；session/JSONL/replay/raw/view/manifest 完整 |

全量回归的 22 个跳过为 Docker 执行 15、Docker dispatcher 1、Linux process-group 6；不算通过。全量回归后增加了一项 MockTransport demo 测试和恢复终止保护，最终通过的是上表 89 项相关回归；没有把两个结果相加成全量测试数。

```powershell
$env:HARNESS_DOCKER_TESTS='0'
.\.venv\Scripts\python.exe -m pytest -q --basetemp .tmp-r2-regression-01 --junitxml docs/upgrade/evidence/R2-lite/offline-regression.xml

.\.venv\Scripts\python.exe -m pytest tests/test_true_summary.py tests/test_context_window.py tests/test_h4_loop.py tests/test_llm_client.py tests/test_recovery.py tests/test_eval_llm_lifecycle.py tests/test_model_budget.py -q --basetemp .tmp-r2-final --junitxml docs/upgrade/evidence/R2-lite/summary-final.xml
```

这些命令是已执行记录。复跑应另选临时目录和报告名，以保留证据。测试用 httpx.MockTransport、fake provider 和临时 workspace，不访问付费 API。

## 正负证据与恢复检查

- 成功：缓存摘要；重新恢复不重复计数/调用；原始 hash、半开消息区间、source snapshot seq、source step 范围可对应。
- 失败：非法 JSON、截断、缺 finish reason、额外字段/重复 JSON key、tool call 输出都不注入；已消费的 usage 仍结算。masking 也塞不下时拒绝。
- unknown：缺 usage 保留 token/货币预留，实际费用 null；provider 不可用没有 fixture 冒充 llm_success。provider usage 越过预算时保留实际计数并停止。
- 生命周期：局部超时有记录；run deadline/取消向上传播；取消后不发下一主模型请求。adapter 复用 host HTTP，不关闭 borrowed client。
- 三个真实进程退出点：summary.started、summary.settled、context.prepared。resume 后摘要不重复付费，之前写入的 `calls.txt` 仍只有一次追加。settled/prepared 后最终总账是 2 个主模型 fixture + 1 个摘要 fixture；known tokens 为 20 + 120 = 140，分账可核对。replay 无模型/工具执行。
- 最终 MockTransport demo 覆盖 manifest → session → JSONL → result/replay；仅 1 次摘要 request，0 次主模型 request。它是 adapter 合约证据，**不是一次真实付费摘要成功**。

首次 pytest 在 Windows 沙箱创建的临时目录遇到 WinError 5；后续测试使用宿主离线执行。`fixture-01/` 同样在 SQLite writer.lock 创建时因 ACL 失败，保留其准备阶段产物，不能视为成功 demo；`fixture-02/` 为随后成功的宿主 fixture。一次全量回归的自动审批等待超时后按提示重试成功，不是测试失败。fixture manifest 各自保留运行当时的 source fingerprint；最后源码的 adapter/恢复行为以 summary-final.xml 为准。

## 仍未验收的边界

R1 的 `summary_calls=0` 和 fixture 文本不证明真实摘要。本轮已交付真实 adapter 与完整宿主管理路径，但**真实提供方端到端调用仍未运行**。运行前需用户选择模型与美元上限，核实价格/上下文/非流式协议，配置宿主 key 与 `thinking: disabled`。完整命令模板见契约文档。

本次只借用主模型的客户端/模型，不提供第二模型路由、自动重试或递归摘要。仅连续完整且未保护的旧工具批次可摘要；输入超限可降级/拒绝，不自动切片。币种只支持 USD，成本是价格表估计或保守预留，不是账户账单。source_event_range 引用保存完整原文的 snapshot，source_step_range 是原始 assistant turn；不是捏造逐消息独立 event ID。

非持久 run 只有内存账本/原始历史；恢复保证需要 RunSession。started-only 时不能判断远端是否扣费，故保守停止。既有 Docker 中断恢复限制保持不变。字节/token 估计不是 tokenizer 实测；摘要语义正确性、真实 latency/cost 和 coding-agent 成功率收益均未验收。即使后续单次真实摘要成功，也只能先作为 context-policy 功能证据。
