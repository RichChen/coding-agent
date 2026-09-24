# A5 可用 Memory Pool 建设合同（轻量版 v2）

日期：2026-09-22。目标是得到一个小而真实、可追溯、可继续扩展的 memory pool。20 个历史候选是来源上限和去重边界，不是要求在建池前把 20 个都做成研究级完整实验；第一阶段允许只得到约 12–15 条有效 `MemoryRecord`。本合同只规定 Cursor 的执行和证据要求；本轮交接不运行实现、provider、model、memory build 或 pilot。

## 必须守住的边界

- 候选清单仍固定为 `pilot20-harness-manifest.json` 的 20 个 memory sources，含四个 history subset；不得增加来源、删除来源、把 target 答案当 memory，或用 empty pool 冒充完成。可以有来源失败、无效或暂不采用。
- 每条入池记录必须来自真实的公开轨迹：agent 实际看到的公开 issue/source、实际动作、实际公开验证和失败都要能回读。不得伪造轨迹、倒填时间、把私有 F2P/P2P、gold patch、test patch、hidden tests、私有 grader 输出写进 public memory。
- 每条记录必须绑定 `source_id/canonical_id`、repo、base revision、source tree/image hash、trajectory/run/attempt id、公开 artifact hash、独立 grader receipt（或明确的可接受验证 receipt）和 provenance review。失败、unknown、环境错误、重试和费用都进账，不升格为成功记录。
- public source image 与 private grader/known-good image 严格分离。完整仓库可以通过 immutable image base + bounded typed delta 传递；8 MiB/2048 只限制 runtime transport，不得裁剪代码或测试树。agent 不得接触私有答案、私有测试或私有镜像。
- 付费执行有硬上限和独立 ledger。当前 coding-agent 的 20 jobs/40 attempts/240 pilot 只是既有计划，不能自动启动，也不能把 attempt 数写成 record 数；memory build 不从 pilot 账本偷用额度。未知用量保持 reserved，直到 reconciled。
- 当前合同不把 A5 的 24 题全量预检、20×4×3 pilot、统计显著性或全量独立 full-repo grader 因果实验作为建池前置条件。它们是后续研究升级，只有另立实验合同并获授权后才执行。

## 现有证据如何使用

`62-history-baseline-retry` 的四行真实记录可作为候选 baseline/environment 证据：它们分别显示 `baseline_ready`、known-good pass、collection/image/cleanup 引用；旧 62 的 ACL/buildx 失败保留为历史失败。它们不能自动成为 grader-ready 或 memory record。

`66/67` 的旧校准只做 collect-only，且阴性结果由常量生成；它们只能作为线索，不能继承 grader-ready。`57-remaining16-baseline` 中的五个异常（Django 11001/11019 mismatch、SymPy 12236 known-good fail、pytest 5413/5495 collection/known-good fail）记录为待诊断来源，不阻塞先做少量 smoke/build；只有某个来源实际要付费建池时，才必须先达到该来源的最小运行 gate。不得把 Django 的 method-level mismatch 偷换成“任意 F2P 失败即通过”。

71/72 的 20/11/11/11 和 shared approval 数字不是本合同的验收基线；它们反映旧聚合逻辑和离线 fixture。Cursor 必须从新 attempt 的逐条证据重算采用、失败和阻塞数量。

## 最小可运行 gate（只对实际采用或付费的 source 强制）

一个 source 可以进入 smoke/build，必须有：

1. 完整 public source tree 与固定 base revision；source/image/tree hash 和 bounded delta 可复核。
2. 可启动的 repo-specific environment；至少一次真实 collection 或目标测试运行，记录 exact test identity、依赖、退出状态和 cleanup。
3. agent 可见输入只含 public issue/source；private patch、gold、hidden test 和 private grader 只留在 host。
4. 候选结束后有独立验证 receipt，能区分 pass、fail、invalid_env、missing_receipt 和 timeout；不能只看 stdout 或 exit 0。
5. provenance 记录包含 source、trajectory、validation、review 时间和所有失败/重试引用；未经人工或规则审查不得进入 `validated`。

若来源要使用完整 full-repo grader，才额外要求 frozen collection、candidate delta path check、baseline/known-good 对照、receipt identity、input integrity 和 cleanup。只做 smoke 的来源不能声称完成 full-repo calibration。

## S0：建立候选索引和可追溯状态

**输入。** 读取 `configs/a5/image-backed-handoff.json`、`pilot20-harness-manifest.json`、model/price/fingerprint 文件；coding-agent 的 canonical handoff、consumption manifest、funding contract；以及 23/48/53/55/57/58/61/62/62-retry/66/67/69/71/72 的必要 manifest、receipt、日志和 artifact hash。源码只读核对 transport、image tree、receipt、repo grader 和 budget 接口。

**交付。** 新建一个不覆盖旧证据的 attempt，生成 20 行 `candidate-index.jsonl`（字段至少包括 `source_id, repo, base_revision, source/tree/image_hash, transport_status, environment_status, collection_ref, baseline_ref, trajectory_ref, grader_ref, cleanup, provenance_status, failure_refs, cost_refs, decision`），另有 `artifact-manifest.json`、`evidence-precedence.json` 和 `decision-log.json`。明确 retry 与旧失败的合并规则：同 source/revision/tree/runner 才可复用；冲突并列；collect-only/未知不变成 ready；失败保留。

**验收模板。**

```powershell
.venv\Scripts\python.exe scripts/<candidate-index-cli> --manifest configs/a5/pilot20-harness-manifest.json --evidence-root docs/upgrade/evidence/<NEW-S0> --output-dir docs/upgrade/evidence/<NEW-S0>
.venv\Scripts\python.exe scripts/<candidate-index-cli> --verify-artifacts --index docs/upgrade/evidence/<NEW-S0>/candidate-index.jsonl
```

若 CLI 不存在，Cursor 只实现生成上述最小索引所需的接口和定向测试。S0 成功条件是 20 个身份可追溯、旧成功/失败均保留；不要求 20 个 source ready，也不要求 full grader。

## S1：选择 4–6 个多样来源做 smoke/build

从四类 repository（优先 Django、SymPy、scikit-learn、pytest）选择 4–6 个证据最完整、环境风险不同的 source，覆盖至少两类成功/失败情形。优先复用 62-retry 的真实 checkout/image/collection；不为凑数量重跑 24 题。每个选中 source 先做最小 gate，再决定是否产生 trajectory/build attempt。

每个 smoke 输出一个独立目录：public input manifest、source/image/tree hash、trajectory（公开观察/动作/公开验证/失败）、candidate snapshot/delta、独立 validation/grader receipt、cleanup、成本和 provenance review。失败也输出同样字段并标 `failed` 或 `invalid_env`。不得把 gold patch 复制成 candidate，也不得把私有 grader 结果写入公开轨迹。

**成功条件。** 至少 4 个 source 完成真实端到端 plumbing，其中可以包含失败；至少 2 个 repo family；每个结果可从 source→trajectory→validation→decision 回溯。若一个 source 的环境失败，记录后换下一个候选，不把单题失败推广成全池阻塞。

**命令模板。** 只在 Cursor 后续执行且确认参数存在时使用；本轮不执行：

```powershell
.venv\Scripts\python.exe scripts/<source-smoke-cli> --source <source-id> --public-input <manifest> --output-dir docs/upgrade/evidence/<NEW-S1>/<source-id>
.venv\Scripts\python.exe scripts/<validation-or-grader-cli> --assignment <private-host-assignment> --output-dir docs/upgrade/evidence/<NEW-S1>/<source-id>/validation
```

## S2：扩展到约 12–15 条有效 MemoryRecord

只有 S1 的 provenance、隔离和 receipt 链路稳定后才扩展。按 repo family、缺陷类型、依赖和验证质量选择更多候选，最多使用固定 20 个 source；不要求剩余候选先完成 full-repo grader calibration。每个实际要付费 build 的 source 在 build 前必须单独通过最小 gate、预算 reservation、public/private review 和 source-specific failure disposition。

记录生成与 promotion 分离：`candidate`、`validated`、`rejected`、`blocked` 四态；15 条目标不是承诺。只有具有真实公开轨迹、公开验证 artifact、独立 receipt、依赖/provenance review 和可回读 hash 的 candidate 才能 promotion。失败/unknown/retry 不因数量不足而 promotion。S2 输出 `memory-pool-candidates.jsonl`、`validated-memory-records.jsonl`、`failure-ledger.jsonl`、逐 attempt artifact manifest 和成本 ledger；报告实际有效数量、repo 覆盖与未决风险。

S2 的停止条件是：任何 record 无法绑定真实 trajectory 或 receipt；private data 边界无法证明；ledger 超过硬上限；重复失败无新证据；或剩余候选只能靠伪造/猜测补齐。停止时交付可用的部分池和明确缺口，不把“未达 15”写成成功，也不强行扩大到 20。

## S3：可选研究升级与公开交接

当轻量池已经可用，另立版本化合同才可选择：

- 对所有 20 sources 完成 24 题/20-source 全量环境、baseline、grader preflight；
- 为每个 source 执行真实 full-repo candidate grader calibration 和阴性拒绝路径；
- 执行固定 20×4×3 pilot、预算统计、显著性/因果分析和冷 snapshot；
- 在两端代码稳定后重冻 source fingerprint，并接入正式 B0–B3 importer。

这些项目是研究质量升级，不是本合同的 memory pool ready 条件。若只完成 fixture receipt wiring，公开交接必须标 `fixture_only`；若没有真实 provider/paid run，必须标 `model_calls=0`、`paid=false`。公开 handoff 只含 public source、接口、hash、状态和下一步，不含 gold/test patch、hidden tests、私有 grader 或目标答案。

## 回滚、预算和最终交付

所有 attempt 使用新目录和新 schema；禁止删除或覆盖旧 evidence。中断后从最后一个完整 attempt 恢复，不重跑已有有效结果。一次实质修复后最多一次针对性复验，仍失败就留账并继续其他 source。

本合同最终交付为：合同引用的新 attempt 路径、4–6 个 smoke/build 的 provenance 与 receipt、约 12–15 条（或实际数量）validated/candidate 状态、失败和成本 ledger、最关键缺口，以及必须另行决定的 paid scope/研究升级。建池可在少量 source 达到最小 gate 且用户明确授权预算后启动；本轮交接本身不启动任何付费操作。
