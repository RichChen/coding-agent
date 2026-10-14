# A5 离线验收记录

2026-09-21。范围为预先写下的 [A5-PLAN](A5-PLAN.md) 与三个任务包；E-A1 B0–B3 离线协议和基础设施已交付。没有修改 H4 实现、另一仓、旧 L0/L2/L5/D0–D3 报告，没有调用真实模型、实现 H6 或运行多任务 pilot。

## 产物与能力边界

- [离线报告](../../reports/upgrade/a5-offline-20260921-v1/report.md)、[完整结果](../../reports/upgrade/a5-offline-20260921-v1/results.json)、[artifact hash](../../reports/upgrade/a5-offline-20260921-v1/artifact-manifest.json)。4 synthetic dev smoke、16 决策，全部排除主分母；repair success=null、0 external model calls、0 actually_injected。
- 合同、dataset/memory-build/empty manifests、每个 task 的冻结 snapshot、公开任务/事实/历史索引、逐项 decision、独立 private smoke checks、源码/config hash 均在上述新目录。empty 场景用单独空 snapshot；同任务四变体用同一 snapshot。其余三场景共用一条 human-authored 历史和人工 validation fixture，不能作为真实历史复现证据。
- B0 无增强；B1 lexical set overlap；B2 结构化 procedure；B3 只增加 current validity。empty/valid/known_stale/unknown 的 B3 selected 分别 0/1/0/0。候选窗口 top-3，最多注入 2 条/4096 UTF-8 bytes；整条超额拒绝、不截断。B1–B3 共用来源、生命周期、冲突和重复门槛。
- common profile 固定 harness-react/none/docker_linux、工具、retry 和统一 calls/tokens/wall；本轮仅冻结、比对合同和 task budget，不执行或声称验证宿主限额。`ResultRow.profile_hash` 是可信 host importer 应提供的绑定，单靠哈希不能证明运行时实际配置。
- requested/selected、prepared view、actual receipts 分开。实际注入须有候选 hash/range、evidence ref、修复模型 operation/attempt。未提供 host receipt 时保持未确认；不生成 observed_following 证据。此审计函数校验关联，调用方仍须验证引用所指的 host artifact。
- 成本保留 failed/unknown 和额外调用；dev 单列、build 逐 memory_id 对账，按固定 unique target N 摊销。重复 run/attempt、漏 started attempt 拒绝，主行缺失使 full_cost=null。这里的 full_cost 仅涵盖已提供模型用量；机器/人工费用未定价，未观测的 host inventory 不能由离线代码自动发现。

## 实际执行与测试

使用已有 Python 3.11.15 环境，未安装依赖。定向：**39 passed in 1.01s**，见 [targeted.xml](../../reports/upgrade/a5-verification-20260921/targeted.xml)。扩大回归：**222 passed in 64.50s**，见 [regression.xml](../../reports/upgrade/a5-verification-20260921/regression.xml)。两者重叠，不相加。

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PATH='C:\Users\Administrator\.conda\envs\coding-harness;C:\Users\Administrator\.conda\envs\coding-harness\Scripts;' + $env:PATH
& 'C:\Users\Administrator\.conda\envs\coding-harness\python.exe' -m pytest tests/test_a5_contracts.py tests/test_a5_variants.py tests/test_a5_audit.py -q -o addopts='' -p no:cacheprovider --basetemp=traces/upgrade_a5_20260921_04 --junitxml=reports/upgrade/a5-verification-20260921/targeted.xml
& 'C:\Users\Administrator\.conda\envs\coding-harness\python.exe' -m pytest tests --ignore=tests/test_cli.py --ignore=tests/test_llm_ablation.py --ignore=tests/test_external_baselines.py --ignore=tests/test_phase7_benchmark.py -q -o addopts='' -p no:cacheprovider --basetemp=traces/upgrade_a5_regression_20260921_01 --junitxml=reports/upgrade/a5-verification-20260921/regression.xml
& 'C:\Users\Administrator\.conda\envs\coding-harness\python.exe' -m ruff check reposkill_agent tests scripts --no-cache
& 'C:\Users\Administrator\.conda\envs\coding-harness\python.exe' scripts/run_a5_offline.py --output reports/upgrade/a5-offline-20260921-v1
```

Ruff 输出 `All checks passed!`。离线脚本 exit=0，输出 4/16/0/0。复跑须换新的 basetemp/output，保留原证据。Windows 沙箱内 pytest 临时目录曾出现 WinError 5，因此测试经执行审批运行；一次自动审批超时未启动命令，按允许的一次重试成功。不是模型/网络审批。排除旧 CLI 默认写报告、外部 baseline 和全量 benchmark，故不称全套测试通过。

保存后只读复核：从冻结合同、dataset/memory manifests 和 results 中的行调用 `summarize`，重建的全部字段与保存值相同；artifact-manifest 中 22 项字节 hash 全部一致，code-manifest 中 8 个实现/config 文件与当前版本一致。10 个本批文档/README 中 54 个本地链接全部存在。累计 diff 实际生成 59 个变化文件（含前期 TP/H4，不作为 A5 独有文件数）。

覆盖来源/泄漏/版本/profile 防线、候选配额与冲突、task 身份非干扰、字节预算、真实注入必需证据、错误 hash/attempt/重复/矛盾收据、build 漏账、dev 成本、缺行/失败/invalid_env/degraded、重跑不覆盖首结果、未知费用及 artifact hash。H4 adapter/公开私有边界/原 memory/validity 同时回归通过。

## dry-run 与后续边界

模板：[12 题](../../configs/a5/pilot-12.json)、[20 题](../../configs/a5/pilot-20.json)。均为 4 变体×3 repeats（组织 seed=42/43/44，不承诺 provider 确定性）。在线上限分别 144 runs/864 calls、240 runs/1440 calls；输入/输出分别 6.912M/1.728M 与 11.52M/2.88M tokens。若每百万单价为 P_in/P_out，公式为 `6.912*P_in + 1.728*P_out` 和 `11.52*P_in + 2.88*P_out`。规则/人工 builder 本批 0 模型 calls；未来 LLM build 要独立记账和预估。

未填真实 heldout、模型 snapshot、verified 价目、currency 或单 run/总货币上限，金额估计为 null、real_api_enabled=false。没有真实 pilot 执行入口。下一阶段须先审核并冻结真正来源与目标数据、宿主 profile/工具/限额及完整 receipts importer，再在明确付费范围内运行。不得将合成 dev 改名当 heldout，不承诺正收益或显著性。

## H4/H5 既有证据与历史保留

只读核对另一仓的 `docs/upgrade/R1-CLOSEOUT.zh-CN.md`、`H5-INTEROP.zh-CN.md` 和 `evidence/H5-interop/real-04/summary.json`。以 real-04 JSON 为准：off/on 各 4 calls、grader 各 4/4；合计 provider 14,355 tokens，实际账户 cost_usd=null。on requested=2、prepared_view_injections=5、proposals_rejected=3、replay/canary 检查通过；prepared-view 不是模型采用。H5 文本旧表的 14,133 tokens 和 2/2 是其他历史批次，不混用。本轮未重跑或重新独立评测该真实 patch，未修改另一仓或发协调消息。

本仓 `harness_h4.py`、`h4_fixture.py`、`test_harness_h4_adapter.py` 的当前 SHA256 与 `reports/upgrade/h4-review-20260921/manifest.json` 的 after_sha256 相同。保留 h4-reference-lock 与交接 v2 原件；README/接口/计划仅加最新状态说明，不把早期 H4 限制继续当现在的阻塞。

## 实际变更审阅

工作目录没有可用 Git 元数据，未创建提交。A5 新增源码为 `reposkill_agent/experiments/{__init__,contracts,variants,audit,offline}.py`、离线脚本、3 个测试和 2 个 pilot 配置；新增计划/3 任务包/本验收文档，更新 README 和四份状态/接口说明。

完整升级累计 diff 由 `scripts/upgrade_snapshot.py compare` 对 `baseline/upgrade-20260919-tp01-04/source.zip` 生成，保存在 [累计变更](../../reports/upgrade/a5-review-20260921/changes.diff)和[hash 清单](../../reports/upgrade/a5-review-20260921/manifest.json)。它包含 TP01–04/H4，**不是只含 A5 的 diff**；文档不在旧快照 allowlist 的部分由当前版本和链接直接审阅。离线包的 code-manifest 独立固定本批实现/config hash，旧历史报告未覆盖。

2026-09-21 后续授权更新：用户已批准正式 pilot 约 50 CNY，并授权必要的付费记忆建池。pilot 按参考价的理论 token 上限为 46.080 CNY，pilot ceiling 为 50.000 CNY；memory build 使用独立 ledger。准备包已扩为 20 个 build jobs、40 个 build/retry attempts，实际模型调用仍为 0。新增资金/建池回归后扩大离线回归为 **234 passed in 63.81s**，见既有 funding regression。预算已授权不等于宿主运行已就绪；仍需 harness 整仓 grader、model/price binding、分账 ledger、公开基线和 receipt importer。没有这些条件，不启动 build 或 pilot。
