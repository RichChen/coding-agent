# A5 harness gate v1

2026-09-21 canonical 消费修订。该文件是 coding-harness 侧的下一阶段合同。coding-agent 固定了 20 个目标题、20 个 memory-build sources，其中 4 个来源属于初始历史预检子集；这是计划清单，`runnable_frozen=false`。本仓负责大仓快照/增量、整仓 grader 接线、模型/价目绑定、人民币账本和 B0–B3 收据导入。当前只做离线准备，`paid_build_started=false`、`paid_pilot_started=false`、model calls=0。

## 固定池与分母

来源是 SWE-bench Lite revision `6ec7bb89b9342f664a54a6e0a6ea6501d3437cc2`，source-lock SHA256=`53f50508569127a2b3e88a10532fbd0049f40196e3076f8bfc4e314a295381a0`，公开审查实际 SHA256=`d1fe518b3b697eb3a992db6ba24a4786c98c7c5f04766c09286e2502d1773ebd`。旧声明缺少 `3b`，仅保留在旧 evidence，不用于新绑定。本仓 `configs/a5/pilot20-harness-manifest.json` 绑定以下宿主入口：

- `D:/crq/src/coding-agent/configs/a5/canonical-handoff.json`，SHA256=`d18d9fa78da00230c30d62c61abce168b91812871d3435e14702aad7a761774c`。
- CLI 使用 `D:/crq/src/coding-agent/configs/a5/pilot20-harness-consumption-manifest.json`，SHA256=`33ab6922caf6909888d672a8d97df49f305ed4cdabb8c402dfca4bca88cb0180`；其中有逐项 canonical/opaque ID、job、repo、commit 映射。

`historical_pool=4` 仅是 `preflight_history_subset` 的旧 CLI 别名，对应 django-10914、sympy-11400、scikit-learn-10297、pytest-5103（完整 canonical IDs 见 manifest）。完整 memory pool 始终为 20 个来源，保留原 20 jobs / 40 planned attempts，未执行。B0/B1/B2/B3、3 repeats、seeds 42/43/44、240 planned task-runs 不变。历史来源不是现成的 validated MemoryRecord；必须以真实公开轨迹和宿主收据重新验证。

公开任务只允许 issue/problem statement、base revision、公开 provenance 等 allowlist 字段。gold patch、test patch、hints、F2P/P2P 和私有 parquet 不得进入 agent context、公开 snapshot 或 model prompt。不能将现有 Flask-4992 环境套给 Django、SymPy、scikit-learn、pytest 或 Sphinx；每题都必须单独记录 source tree、image、Python/pytest、collection 和 baseline 失败。

## 大仓传输与快照

现有 Docker runtime 接口硬限制总传输 8 MiB、2048 files；该限制不提高、不通过裁剪绕过。`src.eval.a5_snapshot` 提供完整源树 manifest、文件级 SHA256、完整 archive SHA256 和 7 MiB content-addressed chunks。超过 runtime 限制时 transport mode 必须是 `image_backed_base_plus_delta`：完整源码/测试在可信镜像 build input 中保留，agent 停止后只传相对 frozen base 的 candidate delta。delta 仍执行 allowlist、base tree hash、candidate tree hash 和 8 MiB runtime 校验。

“分块”只是可验证的 build artifact 组织，不是把缺失 chunk 静默删掉；manifest 的 file_count、total_bytes、archive_bytes、每个 chunk hash 必须全部对上，缺块/错块拒绝。候选 snapshot 不再要求把整个大仓重新穿过 runtime transfer；如果 delta 也超过限制，任务为 invalid_env，不能回退到裁剪仓。

## 环境与基线 gate

`configs/a5/environment-preflight.template.json` 先固定列出 24 个 task inventory；`rows` 仍为空，不能当作运行证据。正式填充时每行必须来自对应任务自己的完整仓库和 pinned image，并写出 collection hash/count、Python/pytest、baseline status、失败 nodeids、清理状态和 model_calls=0。目标题 baseline 必须复现该题原始缺陷；历史题也必须单独完成 baseline 失败/环境判定。任何缺行、复用 image/source、collection 改变、测试资源缺失、环境失败未标注，均保持 blocked，完整分母不缩小。

旧 Flask 整仓 grader 证据仍只证明 Flask-4992；它不是 A5 24 题的环境证明。A5 需要针对每个 repo 的完整 source archive、dependencies、pytest collection 和 private grader contract 另起 evidence attempt。

初始 20 targets + 4 history gate 不覆盖其余 16 个 memory sources。全部 20 个来源均须完成自身 repo/environment/baseline/grader preflight；4 个子集的收据仅适用于精确匹配的来源，不能解锁其余 16 个。缺失、unknown、失败或 invalid_env 始终 blocked。

## model snapshot 与价格

`configs/a5/model-price-binding.pending.json` 是 fail-closed 占位，当前不能作为付费绑定。正式绑定必须同时有 provider、确切 model snapshot/revision（不是裸 `deepseek-flash` 字符串）、CNY currency、官方价目 URL、retrieved/effective date、缓存命中/未命中输入和输出单价，并由宿主标记 `verified=true`。价格截图/旧文档参考值不能直接当现价，也不能拿 USD 表硬换算 CNY；若价格、币种或 snapshot 不完整，ledger 在首个付费调用前拒绝。

## CNY 全局账本与阶段上限

预算 scope gate 为 `blocked_independent_build_budget_pending_runtime_alignment`。canonical 要求 pilot cap 50.000 CNY（参考 token ceiling 46.080），memory build 独立预算、独立分账，由宿主统一管理。本轮不改预算运行代码；现有 `A5BudgetPlan` 的 combined 50 / build 3.840 / pilot 46.080 / reserve 0.080 是待替换的旧实现，不能当作已完成分账。20 jobs / 40 attempts 是计划上限，不是模型调用数或已生成记忆数。

后续所有 repair/retry/builder/router/summary/verifier/grader attempt 都必须带唯一 `operation_id`、component 和 phase 入账。预留按缓存未命中价格计算；provider usage 完整时按同一绑定价目结算，unknown/失败/中断保留原预留，不释放成“免费”。缓存节省不能自动扩题，四舍五入不能突破硬上限。

金额是硬拒绝条件，不是报告估计。ledger 无 verified price binding 时不能 reserve；即便用户已授权约 50 CNY，也不能绕过环境、fingerprint 或 receipt gate。

## B0–B3 接线与收据回传

`src.eval.a5_receipts` 固定 `a5.receipt.v1`。每条 receipt 必须绑定 task/phase/variant/repeat、格式正确的 64 位 source snapshot/model binding/双方 source fingerprint hash、operation_id、唯一 model attempts、CNY ledger snapshot、grader status 和 injection refs。B0 必须没有 injection；B1–B3 的每条注入必须同时有 candidate hash、source/evidence hash/ref，不能因为 prepared view 存在就声称模型 following。导入函数对 schema、attempt identity、绑定漂移、B0 无注入、B1–B3 缺证据、ledger schema 和 grader status fail-closed；缺 receipt 保留 missing/invalid_env，不能删除分母。

## 双端 source fingerprint

`configs/a5/source-fingerprint.pending.json` 只允许在双方代码稳定后填入 harness 与 coding-agent 两个 fingerprint，并把 status 改为 `frozen_after_both_sides_stable`。任何一侧新增/修改源码、runner、配置或 grader 后都必须重新生成双端绑定；不能沿用 Flask、R2 或 A5 准备阶段旧 hash。当前 harness fingerprint 只能作为工作区诊断，不能代替双端 freeze。

## 当前执行状态

运行 `python scripts/a5_preflight.py --manifest D:/crq/src/coding-agent/configs/a5/pilot20-harness-consumption-manifest.json --environments configs/a5/environment-preflight.template.json --model-binding configs/a5/model-price-binding.pending.json --fingerprint-manifest configs/a5/source-fingerprint.pending.json --output <new-dir>` 只做离线 gate，预期返回 exit 2，并写出 `readiness.json`。旧 CLI 只检查初始 24 题，未实现 20 来源逐项门禁或预算分账，即使返回 ready 也不构成 paid 许可。后续执行前仍须全部满足：

1. 24 行独立整仓 environment + baseline failure receipts；
2. verified model snapshot + current CNY price；
3. dual source fingerprint frozen after both sides stable；
4. B0–B3 receipt importer 与 host operation/attempt ledger 联调；
5. public/private separation、license/provenance、source chunk hashes 和 full denominator audit。
6. 每个 memory source 自身完整 repo/environment/baseline/grader preflight；
7. 独立 build 预算与 pilot 分账运行机制对齐。

本轮 gate 仍为 blocked；不执行 checkout、build image、Docker、baseline 或模型。输入一致性 adopted 仅确认消费，不代表 environment ready。全部 20 memory sources 仍 blocked；后续满足对应来源及共享 gates 并获得执行指令，才能进入 paid build。完成真实 receipt、公开轨迹审核和 cold memory snapshot 后才讨论 240 条 pilot runs。新消费审计与 CLI 原始结果保存在 `docs/upgrade/evidence/A5-harness-preflight-11-canonical-consumption/`，旧 evidence 保持不变。
