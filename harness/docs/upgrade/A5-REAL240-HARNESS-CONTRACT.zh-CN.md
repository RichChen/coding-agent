# A5 真实 240 Pilot：coding-harness 侧执行合同 v1

日期：2026-09-22。目标是为固定的 240 次真实 pilot 运行提供可审计的 harness 接线、预算、receipt 和分波执行条件。240 的固定矩阵是 20 个 target × 4 个 variant（B0/B1/B2/B3）× 3 个 repeat，seed 为 42/43/44。合同不把 240 扩大成更多运行，也不把 smoke/build attempt 当 pilot run。

本合同只约束 `D:/crq/src/coding-harness`。agent 侧的 B0–B3 语义、memory 消费清单和 target grader 接线由另一个任务并行准备；双方完成各自冻结后才能进入真实付费 pilot。当前不启动 provider、model、memory build 或 pilot。

## 当前可用事实

- `docs/upgrade/evidence/A5-memory-pool-76-s2/s2-status.json` 记录了 11 条 `validated` memory record、4 条失败、5 条 blocked。11 条的范围是 `public_independent_smoke_receipt_plus_rule_provenance_review`，`private_grader_run=false`；它们可作为轻量 cold snapshot，不能宣传为完整 full-repo grader 证明。
- 11 条具体记录位于 `A5-memory-pool-76-s2/validated-memory-records.jsonl`，carry-forward 五条来自 `A5-memory-pool-75-s1-smoke`，expand 六条来自 76-s2。失败和 blocked 不能从 snapshot 中删除后改写为成功。
- coding-agent 的 canonical handoff 仍为 `runnable_frozen=false`、`validated_memory_records=0`、`paid_pilot_started=false`；20 个 target 仍显示 `awaiting_repo_grader_readiness`。这说明 memory pool 尚未正式被 agent 侧消费，240 尚未可运行。
- 240 的原始计划位于 coding-agent 的 `reports/upgrade/a5-pilot20-preparation-20260921-v4/experiment-contract.provisional.json` 与 `assignments.json`；预算参考为 240 × 0.192 = 46.080 CNY，pilot 硬上限为 50.000 CNY。memory build 账本独立，不从 pilot 额度扣除。

## 不可妥协的条件

1. source、trajectory、memory snapshot、injection、target、variant、repeat、seed、model binding、grader 和 budget 都必须由 receipt 绑定；缺任一关键绑定的 run 保留为 `missing`/`invalid`，不能按失败或成功悄悄吞掉。
2. B0 必须没有 memory injection；B1–B3 每次真实注入必须有 agent 侧 injection receipt、source/evidence hash 和 snapshot hash。prepared view 不能代替实际注入。
3. agent 只看到 public issue、public source 和允许的 memory 视图。gold patch、test patch、hidden tests、private grader、target 答案和 raw private source row 永远留在 host。
4. 运行后由独立 grader 评分；stdout、模型自报、exit code 或“看起来改了文件”不能单独算成功。每次运行都记录 cleanup、完整候选 hash、grader receipt、usage 和 CNY ledger。
5. 240 是完整分母。异常、超时、provider error、unknown usage、missing receipt、invalid_env 和中断都保留在 240 行 assignment ledger 中。
6. 运行上限为 pilot 50.000 CNY；未知用量继续 reservation。不得因为有剩余预算自动增加 runs、repeats、targets 或 variants。
7. 研究统计只能使用合同冻结后的 240 结果。没有预先固定的分析方案，不追加显著性、因果或泛化声明。

## H0：冻结轻量 memory snapshot（现在可做）

**输入。**

- `docs/upgrade/evidence/A5-memory-pool-76-s2/validated-memory-records.jsonl`
- `docs/upgrade/evidence/A5-memory-pool-75-s1-smoke/provenance-review-carry-forward/validated-memory-records.jsonl`
- `configs/a5/pilot20-harness-manifest.json`
- `configs/a5/image-backed-handoff.json`
- coding-agent 的 `configs/a5/canonical-handoff.json`、`pilot20-harness-consumption-manifest.json`、`funding-cny-v1.json`

**允许修改。** 只新增 snapshot/export/audit CLI、schema、定向测试和新 evidence。不得修改旧 73–76 目录、旧 validated record、target 清单或 coding-agent 文件。

**输出。** 新目录建议 `docs/upgrade/evidence/A5-real240-77-harness-preflight/`，至少包含：

- `memory-snapshot.jsonl`：11 条记录的冻结副本，保留 `validation_scope=public_independent_smoke_receipt`；
- `memory-snapshot-manifest.json`：snapshot hash、每行 hash、source ID、repo/base/tree/image、trajectory/validation receipt 引用、record state；
- `public-boundary-audit.json`：扫描 gold/test/hidden/private marker 和路径越界；
- `memory-consumption-contract.json`：agent 可消费字段、禁止字段、cold snapshot 版本；
- `failure-ledger-ref.json`：4 failed + 5 blocked 的引用，证明未被 promotion；
- `artifact-manifest.json` 和可重算的 readiness。

**验收。** 11 条 source ID 唯一，所有 hash/receipt 可回读，snapshot 可独立重算；没有 private marker；不要求 20/20 source ready。任何 record 只能在 `validated_lightweight` 状态下导出，不能自动改成 full-grader-validated。

**命令模板（本轮不执行）。**

```powershell
.venv\Scripts\python.exe scripts/<memory-snapshot-export-cli> --input docs/upgrade/evidence/A5-memory-pool-76-s2/validated-memory-records.jsonl --output-dir docs/upgrade/evidence/A5-real240-77-harness-preflight
.venv\Scripts\python.exe scripts/<memory-snapshot-audit-cli> --snapshot docs/upgrade/evidence/A5-real240-77-harness-preflight/memory-snapshot.jsonl --manifest docs/upgrade/evidence/A5-real240-77-harness-preflight/memory-snapshot-manifest.json
```

## H1：receipt、预算和 240 矩阵预检（现在可做）

**输入。** 240 assignments、provisional experiment contract、model-price binding、source fingerprint、`src/eval/a5_receipts.py`、`src/policy/cny_budget.py`、`src/runtime/session.py` 与现有 receipt tests。先核对 240 行是否恰为 20×4×3，target/variant/repeat/seed/assignment ID 是否唯一且与 canonical mapping 一致。

**允许修改。** 只允许在 `src/eval/a5_receipts.py`、最小 pilot receipt/ledger CLI、对应单元测试和新 evidence 中补缺。不得借机修改 agent loop、tool policy、target source、旧 grader 或 memory record 内容。

**必须冻结的 receipt 字段。** `assignment_id, experiment_id, canonical_target_id, agent_task_id, variant, repeat_id, seed, public_task_hash, target_base_hash, memory_snapshot_hash, injection_receipt_refs, model_binding_hash, harness_fingerprint, agent_fingerprint, operation_id, attempt_ids, usage, reservation/settlement, candidate_hash, grader_receipt_ref, cleanup_verified, status, failure_reason, created_at/finished_at`。

**H1 输出。** `pilot-matrix-lock.json`、`pilot-budget-lock.json`、`receipt-schema-lock.json`、`missing-target-gates.json` 和新 artifact manifest。预算锁定 50.000 CNY pilot cap、46.080 reference ceiling、未知用量保留；memory build 单独记账。

**停止条件。** 240 行缺失或重复、B0–B3 语义未冻结、target grader 不可用、model snapshot/price 失效、双方 fingerprint 漂移，均只生成 blocked report，不开始真实调用。

## H2：零模型 fixture 接线（现在可做，不能冒充真实 pilot）

用现有 B0–B3 receipt fixture 和本地 mock 完成最小接线审计：B0 无 injection；B1–B3 缺 source/evidence/hash 时 fail-closed；assignment 错绑、snapshot 漂移、重复 attempt、未知 usage、缺 grader receipt、cleanup false 都被拒绝。fixture 输出必须标 `fixture_only=true`、`model_calls=0`、`paid=false`。

H2 只验证数据链路，不证明模型实际看到 memory，也不证明 target grader 运行。若现有 CLI 不支持这些 fixture，先补最小接口和定向测试，另开 attempt；不得手改 fixture JSON。

## H3：等待 agent 侧冻结后做双端接线复核（依赖 agent 侧）

只有 agent 侧完成以下交付后才能进入 H3：

- B0/B1/B2/B3 的运行语义、memory view、注入位置和 receipt schema；
- 20 target 的 canonical/agent/public task/base mapping 和 target grader readiness；
- coding-agent 消费 11 条 `validated_lightweight` snapshot 的 manifest/hash；
- 240 assignments 覆盖检查和不变的 20×4×3 矩阵。

H3 由 harness 复核两端 manifest/hash、source fingerprint、model binding、memory snapshot 和 receipt schema；任何不一致都回到 H1/H2 修复，不开始 provider 调用。

## H4：真实 240 分波执行（依赖 H3、另需明确 paid pilot authorization）

240 运行必须使用原矩阵，不增不减。建议按 5 波执行，每波 4 个 target × 4 个 variant × 3 个 repeat = 48 runs；波内可串行或受控并行，但每波结束必须审计 receipt、预算和 cleanup 后才进入下一波。波次只是恢复和审计边界，不改变统计分母。

每一波至少保存：assignment ledger、raw session/event、每 run receipt、injection audit、candidate snapshot/hash、independent grader result、usage/settlement、cleanup、failure ledger 和 artifact manifest。中断后从最后一个完整 assignment 恢复，已完成 run 不重放；不确定费用保持 reservation。

**每波通过条件。** assigned 行数正确；B0/B1–B3 注入状态正确；target、source、variant、repeat、seed 和 snapshot hash 一致；grader receipt 可回读；无未解释的 cleanup/input drift；累计成本仍低于硬上限。任何一项失败，暂停下一波并生成具体 blocker。

## H5：240 完成后的审计与报告

最终审计必须从 240 条原始 run receipt 重算：每 variant 的 assigned/completed/failed/missing、target-level paired outcomes、usage/cost、memory injection success、grader status、cleanup 和失败类别。缺失 run 不从分母删除；失败不改成环境成功；不要把轻量 memory record 的 smoke validation 解释为 target causal proof。

交付 `pilot-240-readiness/final-receipts.jsonl`、`summary.json`、`failure-ledger.jsonl`、`cost-ledger.json`、`artifact-manifest.json` 和人读报告。研究结论必须引用冻结合同、matrix lock、snapshot hash、model/price binding 和可回读 receipt。

## 并行与依赖表

| 工作 | coding-harness | agent 侧 | 是否现在可做 |
|---|---|---|---|
|11 条轻量 snapshot 导出/边界审计|负责|提供消费字段建议|可以|
|240 matrix、receipt、pilot ledger lock|负责|核对 assignments|可以并行|
|B0–B3 实际注入语义|复核 receipt|负责定义/实现|agent 先做，harness 可并行审计|
|20 target grader readiness|消费 receipt|负责 target mapping/grader 接线|agent 侧必须完成后才能 H3|
|zero-model fixture|负责|提供 schema/fixture|可以并行|
|真实 240 provider runs|负责 orchestration/ledger|负责 agent runtime|H3 后、另需 paid authorization|

## 回滚与停止

所有新输出使用新目录和新 schema；不得覆盖 73–76 或旧 pilot preparation。任何 source、target、memory snapshot、B0–B3、fingerprint、model binding 或预算漂移都使当前 lock 失效。没有新证据的失败不原样重试；一次实质修复后最多一次针对性复验。当前合同完成 H0–H2 即可交给 agent 侧继续；没有 H3 和明确 paid pilot authorization，Cursor 不得启动真实 240。
