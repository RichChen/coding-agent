# A5 离线基础设施实施计划 / experiment-contract v1

本合同在本批代码和 smoke 执行前冻结。范围：E-A1 B0–B3、公平候选、数据/构建清单、结果审计、成本 dry-run；不改 H4，不做 H6/通用 grader，不调用付费 API。R1/H5 的真实单任务联调已由协调方完成；旧 H4 文档的限制是历史快照，不据此重做接入。

## 固定研究合同

问题：同一历史来源和运行底座下，结构化经验与依赖有效性检查的作用和代价是什么？假设：B3 能拒绝必要依赖已变或不明的历史经验；结构化经验是否改善修复不预设答案。

变体：B0 无增强；B1 lexical set overlap（不是 BM25）检索公开原始轨迹；B2 同一排名的 MemoryRecord procedure/skill 表示；B3 仅在 B2 上加 current validity。历史原文与结构化记录严格一一绑定、来源 hash 相同；B1–B3 同分数与候选 top-3，最多 2 条/4096 UTF-8 bytes 注入，超额整条拒绝、不截断、不回填候选窗口。共同来源、secret、生命周期和冲突/重复检查不能在 ablation 中关闭。B2 可使用历史 validated 但当前不兼容记录；B3 invalid/unknown 拒绝。B0 不生成定位等其他增强，四组基础 loop/context/tools/retry/backend 相同。

共同运行 profile：harness react、context none、docker_linux、只用宿主工具、统一总调用 6、总输入 48000/输出 12000（宿主总 token 上限 60000）、wall 600 秒、工具 30、retry 1（占上述总调用）。无 LLM router/摘要/builder；未来开启必须占共同额度、逐 attempt 入账并版本化合同。离线 fixture 不执行此 runtime；这是待宿主核验的配置，不冒充预算已执行。

数据：本批 4 个 synthetic dev smoke（不进主分母），1 条 synthetic memory_build 历史；split 依据合成版本顺序，公开材料与独立私有预期分离。数据清单绑定 source_type、origin、license、repo/revision、issue/artifact hash、duplicate_group、开发暴露和审查证据。跨 split task ID/hash/重复组交叉、目标/未来/diagnostic 来源拒绝。不得声称排除模型预训练污染。真实 pilot 12 或 20 个固定 heldout × 3 repeats，组织 seed=42/43/44（不声称 provider 确定性）；任务清单、模型/价目、数据审查和用户费用上限未齐前只能 dry-run。

主指标：独立 grader pass / 所有 assigned task-runs；partial/fail/invalid_env 保留，缺行计 missing，重跑单独保留但首 attempt 决定主要分母。按 task 跨 repeat 汇总 paired diff，缺对不计算 delta。method_degraded 留在分母、另列。离线 smoke 的修复成功率为 null，不从 selection 或 fixture 结果编造能力分数。

成本：所有 repair/retry/router/summary/builder/verifier/grader attempt 入账，operation/attempt 唯一，失败/unknown 同样保留；无 usage→unknown/null，有 tokens 无价目→cost unknown。全成本含 online、build、dev；按预先固定 unique target N 摊销 build，不按 repeat 再扩大 N。不把金额未知的部分当 0。CPU/墙钟另列，不折算未提供的机器费。

行为成功信号：4 smoke 符合预先声明的空池/valid/known stale/unknown 行为；B3 stale/unknown 零 selected；实际注入必须能绑定候选 hash 与 host model operation/attempt。独立失败信号：来源泄漏、变体配置不一致、stale 注入、缺 receipt 被算注入、成本漏调用、invalid_env 被剔除；任一出现则基础设施验收失败。真实修复收益、显著性和 SWE-bench 声明均不在本批。

产物写新目录：contract、dataset/memory-build manifests、public task/index/prompt 投影、逐任务 smoke/decision/usage、私有 fixture 预期、报告、dry-run、pilot 12/20 配置、源码 hash/diff。合同数据变更必须新版本，不回改结果。

## 三个交付包

1. [A5-01](tasks/A5-01-CONTRACT.md)：合同、manifest 和冻结校验。
2. [A5-02](tasks/A5-02-VARIANTS.md)：公平 B0–B3 决策及 fixture。
3. [A5-03](tasks/A5-03-AUDIT.md)：收据/usage/分母/paired diff、dry-run 和产物。

实施者为本任务；不创建子任务，不修改另一仓。检查命令将在实现后实际执行，再补验收记录。现有解释器和 pytest/Ruff 已于 H4 验证可用。

## 交付状态（2026-09-21）

三个包的离线范围均已交付，合同与成功/失败标准未按结果改写。实际代码在 `reposkill_agent/experiments/`，固定模板在 `configs/a5/`，命令为 `python scripts/run_a5_offline.py --output <不存在的新目录>`。本次 [报告](../../reports/upgrade/a5-offline-20260921-v1/report.md)包含 4 场景×4 变体、0 API、0 主分母；没有真实修复或 heldout 声明。

审计落实包括：未知 usage/cost 保持 null；缺主结果行则完整费用未知；失败/重试/router/summary/builder/verifier/grader 均可逐 attempt 入账；dev 单列；构建声明需绑定 memory_id 的调用记录；重复 run/attempt 拒绝。每行显式提供 started count，宿主负责完整 run inventory 和费用强制执行。这里只校验合同/关联，未给四变体接线真实 runtime；不是第二套预算器。

定向 39 passed，扩大离线回归 222 passed（包含定向和 H4，不相加），全仓 Ruff 通过。命令、边界和实际 diff 见 [A5-VERIFICATION](A5-VERIFICATION.md)。后续仍需真数据审核与冻结、host profile/价目/货币预检、明确 paid-run 范围后才可执行 pilot；通用 grader/H6、付费规模化和旧实验重跑均不在本批。

2026-09-21 后续授权：用户选择 20 题目标，授权前置准备并要求正式 pilot 前停下等待 A5 预算批准。按另存的[准备合同](A5-PILOT20-PREPARATION.md)形成 20 个真实整仓候选与 240 条 planned assignments；候选/公开 DTO 已固定，runnable dataset/memory 尚未冻结。状态、宿主适配缺口和未批准的预算草案见 [20 题准备记录](A5-PILOT20-STATUS.md)，不回写本节早期 smoke 或把准备包当效果结果。

2026-09-21 预算授权更新：用户同意正式 pilot 约 50 CNY，并授权必要的付费记忆建池。新增 [A5-FUNDED-BUILD-v2](A5-FUNDED-BUILD-v1.md) 与 `experiments/funding.py`：pilot ceiling 50.000，参考 token 上限 46.080；memory build 独立计账，固定 20 个 source、40 个 build/retry attempt，目标 15–25 条 validated records。这里的“已授权”只代表费用范围，仍需 harness grader、模型/价目绑定、host ledger 和 public baseline 预检；通过后先建池和冻结 memory snapshot，再运行 240 个 pilot assignments。
