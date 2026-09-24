# R2-lite：真实摘要契约与实施计划

后续状态：用户另行授权后已完成真实 smoke 和 summary/masking 对照，见 [R2-real 验收记录](evidence/R2-real/README.md) 与 [实验合同](R2-EXPERIMENT-CONTRACT.zh-CN.md)。下文“本轮未运行”保留为 R2-lite 离线实施阶段的历史范围，不代表当前状态。

2026-09-21。基于当前源码及 R1 收口证据；本轮授权实现与离线验证，不授权真实 API 调用。R1 的 `summary_calls=0` 与 H4 extractive fixture **不是**真实 LLM 摘要验收。通用 grader、H6、Pro/思考模式、跨仓修改和性能对照不在范围内，也不是真摘要正确性的前置。

## 契约

- 默认 `summary_provider=fixture`，保留四策略及无模型基线。`none/masking` 不调用摘要；`summary/mask-then-summary` 仅在当前视图溢出且存在完整、未保护的旧工具批次时触发。system/task、最近失败、近期写与 tool 配对继续保留。
- 当前 `LoopHooks.before_llm`、`WindowPolicyHooks.before_llm` 和 `AgentLoop._model_view` 已全部 async。保持现有签名，由 loop 统一 await；不增加嵌套 `asyncio.run` 或同步 HTTP。CLI 顶层可以 `asyncio.run`。
- `SummaryProvider` 只接收宿主构造的固定摘要指令、原始 system/task 约束与选定原始批次。LLM adapter 借用已有 `LLMClient`（同模型、同 HTTP 生命周期），不读取 key、不创建第二个 client、不接工具/插件/grader。输出只接受完整 JSON 对象及 `finish_reason=stop`，拒绝工具调用和多余字段；作为明确标记的不可信 user context 注入。
- 输入永远来自 raw history，不能递归摘要此前 summary view。缓存绑定来源 SHA256、消息半开区间和 prompt/config/model 指纹；来源改变拒绝复用。成功记录、失败记录、调用计数和时间/token 额度均可恢复；同源失败也不自动重试。
- 每次真实调用先向宿主共享 ModelBudgetLedger 预留，再持久化 `summary.started`，最后发 HTTP。响应或错误后写 `summary.settled`，原子携带 manager state 与总预算。摘要与主模型 attempt 分账，但共享 run 的 calls/tokens/currency/deadline/cancel。缺失 usage 为 unknown，保留保守预留；估价不是账户扣费。无账本/能力不可用不调用。
- 恢复时 started 无 settled 为 outcome_unknown，不能重新付费。settled 后 prepared 前可以从成功缓存重建；prepared 后直接恢复视图。replay 只 reduce，不执行模型、工具、插件。旧版本 session 不保证跨源码恢复；R1 已归档证据不重写。
- 记录 summary_id、provider/model、prompt/config 版本/hash、raw_message_hash、source_hash、消息区间、来源 snapshot 事件范围、原始 assistant turn 范围、生成 step、usage provenance、费用估计/预留/价格、耗时、压缩前后字节/token 估计与状态。来源 snapshot 指向包含完整 raw history 的 state.saved；不冒充每条消息独立事件 ID。`source_step_range` 为从零起的原始 assistant turn（react loop 中对应原始 step），`snapshot_step` 是保存完整原文时的当前 step。
- 普通错误/非法结构/摘要局部超时按显式 `masking` 或 `reject` 策略处理；masking 仍需窗口准入。取消、run/step deadline、预算耗尽、持久化错误必须停止，不继续主模型。失败文本不包含任意 provider 异常正文，原始事件保留。
- manifest、runtime fingerprint、context events、run result/report 显式区分 fixture/llm。provider 不可用不得生成 llm_success。summary 文本不能转成 tool proposal、system 指令、私有 EvaluationSpec 或插件入口。

## 任务包（同等适用于 Codex / Cursor）

| ID | 改动范围与交付 | 行为验收与退出条件 |
| --- | --- | --- |
| TS-01 | 本文；summary provider/adapter；配置与 factory/window 接线 | 默认 fixture 回归；真实 adapter 借用 HTTP；只在必要溢出调用；完整 JSON/stop/tools 检查；none/masking 零调用 |
| TS-02 | loop、session/reducer、独立摘要账目/事件 | 调用前 durable intent；unknown 不免费；同源缓存；恢复不重置计数；两崩溃窗口不重复调用；取消不继续主模型；raw/hash 可关联 |
| TS-03 | 离线 fake/provider contract 测试；单次 demo CLI/manifest/report；验证记录 | 无网络验证成功/非法/截断/超时/取消/unknown/预算/来源漂移/恢复；准备有付费开关、显式模型/美元上限/价格版本的单摘要 demo；本轮只运行 help 与离线路径 |

依赖顺序 TS-01 → TS-02 → TS-03；只使用一位实现者改共享文件。检查命令按实际新增测试和 CLI 在完成报告中固定。主要风险是付费调用与 SQLite 无法跨系统原子提交，因此 started-only 必须保守拒绝；本地字节/token 估计不是 provider tokenizer。语义摘要可能丢失事实，即使功能验收成功也不能宣称提高 coding-agent 成功率。

指定参考 `C:\Users\23500\Desktop\src\learn-Codex-main` 与 `D:\crq\src\learn-Codex-main` 本机再次检查均不存在；沿现有宿主接口实现，不声称读过参考脚本。

## 实现入口与验证命令

TS-01：`src/runtime/summary.py`、`window.py`、`context.py`、`src/llm/client.py`、schema/factory。TS-02：loop/result、recovery reducer、run/trace/manifest。TS-03：`tests/test_true_summary.py`、`tests/fixtures/summary_worker.py`、`scripts/demo_true_summary.py`。实际证据索引见 [R2-lite 验证记录](evidence/R2-lite/README.md)。

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_true_summary.py tests/test_context_window.py tests/test_h4_loop.py tests/test_llm_client.py tests/test_model_budget.py -q
.\.venv\Scripts\python.exe scripts/demo_true_summary.py --help
.\.venv\Scripts\python.exe scripts/demo_true_summary.py --output-dir runs/summary-fixture-new
```

默认 provider 是 fixture，不读取真实模型配置。真实模式仅生成一次摘要，不发主模型请求、不执行工具；读取现有宿主配置，由 factory 管理认证和 HTTP，finally 关闭。输出包含 `manifest.json`、完整 `raw-messages.json`、SQLite session、JSONL、summary state、view、run result、replay 和 report。

真实 demo 的模板如下（尖括号必须先替换，**本轮没有运行**）：

```powershell
.\.venv\Scripts\python.exe scripts/demo_true_summary.py `
  --provider llm --allow-paid --config <现有宿主配置.yaml> `
  --model <用户选定的非思考模型ID> --max-cost-usd <用户批准的美元上限> `
  --prompt-per-1k <保守输入美元价每千tokens> `
  --completion-per-1k <输出美元价每千tokens> --price-version <价格来源及日期> `
  --output-dir runs/summary-real-new
```

运行前提：用户明确选定模型和金额；配置 `thinking: disabled`；宿主凭据/网络可用；核实所选 provider 支持现有非流式 chat、max_tokens、usage 协议与足够上下文；价格取覆盖缓存/时段差异的保守上界。币种首版只支持 USD，不是账户账单。默认单摘要 512 输出 tokens、65536 输入序列化字节、131072 累计预留 tokens、30 秒单次/60 秒累计摘要时间；同时受 run deadline 限制。主视图 6000 是演示窗口，摘要输入另有独立上限，不把 bytes/4 估计称为 tokenizer 实测。

用户未批准真实调用前，`--help` 和 fixture 路径即可验证入口。已存在目录拒绝覆盖。真摘要不依赖 Docker；以后接入真实修复 loop 的 Docker 恢复限制沿用 R1。
