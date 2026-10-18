# A5 人民币预算与真实建池合同 v2

用户已澄清：50.00 CNY 是正式pilot上限，memory build按需要独立计账，不从pilot扣除。当前指令仅允许canonical handoff收口，不启动任何付费任务。宿主唯一入口为 [canonical-handoff.json](../../configs/a5/canonical-handoff.json)，以 [收口报告](A5-CANONICAL-HANDOFF-RESOLUTION.md) 明确的24题gate及逐来源gate为准；预算授权与环境就绪分别记录。

## 预算分账

截图仅作为用户提供的价格依据：高峰输入未命中 2 元/百万 tokens、输出 8 元/百万；空闲/缓存折扣不用于预留。供应商、确切 model snapshot、官方价目生效时间尚待宿主预检绑定。不是“截图已核实官方现价”。金额用十进制定点计算。

保持 E-A1 的 20×4×3=240 首次 runs、每 run 6 attempts/48000 input/12000 output 等原定合同不变。按截图参考价每 run 0.192 元，理论 token 上限为 46.080 元；pilot ceiling 设为 50.000 元，差额是运行余量，不是自动扩充任务。宿主如只能按分设置限额，应向下取安全配置并重新预检，不能把每 run 四舍五入到 0.20 后仍称总预算没变。pilot 全局账本必须硬限额。

建池目标是 15–25 条已验证 MemoryRecord；当前固定 20 个历史来源，每个预留首次尝试和一次 retry，共 40 个 build/retry attempt。它们使用独立的 memory-build ledger，不从 50 元 pilot ceiling 扣除；实际消耗按 harness usage receipt 记账。不得把 40 次尝试写成 40 条记忆，也不得因失败、unknown 或环境错误自动升格。失败、unknown、重试同样留在分母和账本中。

建池修复模型调用全部由 harness 网关执行，phase=build/component=repair或retry；结构化提炼先用已有规则/人工审阅，不额外建模型客户端。若后来启用收费 extractor，component=builder，仍计 build 分账；模型 grader/router/summary 首批关闭。模型成本与未定价本地机器/人工时间分列。

## 真实记忆池的构建过程

固定来源使用准备 v4 中按同一规则锁定的 20 个 2020 年前候选（Django、SymPy、scikit-learn、pytest 各 5 条）。与 20 个目标 task/base/issue hash 去重；公有 issue 中已有建议原样披露，不拿私有答案做老师。每个 source 单独的新 workspace/container，只挂载它的 base code、公开 issue、公开测试；不挂载目标目录、原始 parquet、hints、gold/test patch 或目标结果。

宿主先用无模型独立 grader 确认历史任务基线/环境可用，然后由基础策略实际修复；记录每次模型、工具与公开检查。候选冻结后独立评测。失败记录保留计费，不通过 gold patch补正后假称模型成功。公有轨迹抽取只读模型实际可见的公开观察、动作、公开验证和失败；私有 F2P/P2P 内容/期待值不进入 raw index 或 procedure。私有 grader pass 只是外部验收，不能包装成 public ValidationEvidence。

规则 builder 先产 candidate；需公开验证 artifact、依赖映射、source/actual run IDs/hashes、逐 attempt 成本与人工审查齐全才可 validated。B1 使用同一允许来源的原始公开轨迹，B2/B3 使用它一一对应的结构化投影；所有目标前冻结 cold snapshot，期间不写入新经验。失败/unknown/candidate 不为提高池大小自动升格。

历史任务的 PR 时间和今天运行轨迹的时间必须分开记录。真实生成的轨迹发生于今天，绝不倒填到 2016–2019。现有 `validate_manifests` 的 `source.occurred_at < target.occurred_at` 把材料年代与实际采集混在一起，不能直接承接 replay-generated 数据；正式导入前需要版本化区分 `historical_source_at`、`trajectory_observed_at`、`validation_checked_at`、`snapshot_frozen_at`、`pilot_started_at`，验证旧来源早于目标来源、构建/验证早于 snapshot、snapshot 早于 pilot。此次只导出真实 build jobs，不伪造可用 manifest 来绕过旧校验。

Sphinx 在原规则下仍缺旧来源，不偷偷放宽到 2020 年后的 issue。20 个旧来源也不保证能得到有用经验，来源年代久可能出现 env 失败；准备来源不等于有效覆盖。空池只允许 plumbing smoke，不能用它替代正式记忆效应实验然后声称完成 A5。构建完报告实际有效池数量、repo 覆盖、依赖检查状态与成本，再冻结可用池。

## 本轮包与验收

交付三个部分：人民币资金合同与算术校验；20 个 build PublicTask/独立评测引用、40 个 attempt 计划及公私分离导出；明确的宿主执行/真实轨迹接收条件和离线测试。新目录保存 hash，旧报告不覆盖。测试覆盖金额校验、目标来源混入、缺失/篡改 artifact、私有 sentinel 与来源清单绑定。不写另一仓、不替用户发消息。

未来先由harness完成20 targets+4 history的24题零模型gate；其余16个memory sources必须逐项另过自身仓库/环境/baseline/grader gate。仅允许对应来源具备后续paid build资格，不能因4条通过而解锁全池；model/price、分账ledger、双端fingerprint与receipt条件也必须齐全。本轮保持prepared_not_started并停在handoff，不调用旧client或provider，不运行240个targets。旧准备包的doc hash属于当时快照，不视为当前运行冻结。

保留准备包：build jobs（本地生成，未入库：`reports/upgrade/a5-funded-build-preparation-20260921-v12/build-jobs.json`）、attempt 计划（本地生成，未入库：`reports/upgrade/a5-funded-build-preparation-20260921-v12/build-attempt-plan.json`）、旧 harness handoff（本地生成，未入库：`reports/upgrade/a5-funded-build-preparation-20260921-v12/harness-build-handoff.json`）、资金合同（本地生成，未入库：`reports/upgrade/a5-funded-build-preparation-20260921-v12/funding-contract.json`）、状态（本地生成，未入库：`reports/upgrade/a5-funded-build-preparation-20260921-v12/status.json`）。20 个 job 为 `prepared_not_started`，40 个 attempt 原状态为 `planned_not_started`，均未执行，validated memory 数为 0。新交接入口为canonical清单；不重建或覆盖旧包。
