# A5 20 题候选准备与预算草案

最新状态（canonical handoff收口）：20 target计划、20 memory sources/最多40次build尝试、4 history预检子集已独立列入 [canonical-handoff.json](../../configs/a5/canonical-handoff.json)。先由harness过20+4的24题gate，其余16来源各自预检后才有对应build资格；本轮一律不付费，不生成MemoryRecord，无runnable freeze。harness历史池命名、旧预算和公开审查hash冲突见 [收口报告](A5-CANONICAL-HANDOFF-RESOLUTION.md)，待宿主消费确认。以下旧阶段记录不能解锁执行。

2026-09-21。候选 intake、公开输入审查、公私分离和 assignment 计划已完成。用户随后授权约 50 元人民币，并支持必要的付费建池；因此预算授权状态已从“待批”更新为“已授权”，但**正式 pilot 和记忆建池仍未开始，付费模型调用为 0。20 是真实候选数，不是已完成环境验收的可运行任务数。** 需要 harness 的 checkout/环境/grader/插件接线暂缓；最终 dataset/memory/runtime 还不能宣布 runnable frozen。

本批遵循事先保存的 [前置合同](A5-PILOT20-PREPARATION.md)。没有改 E-A1 的四变体、指标、split 原则或预算配额；没有修改另一仓、启动 Docker、安装依赖、执行 benchmark 源码/测试、调用模型或发送协调消息。也没有把另一任务的付费授权用于 A5。

## 已交付

- [最终候选包 v4 报告](../../reports/upgrade/a5-pilot20-preparation-20260921-v4/report.md)、[完整清单](../../reports/upgrade/a5-pilot20-preparation-20260921-v4/candidate-inventory.json)、[准备状态](../../reports/upgrade/a5-pilot20-preparation-20260921-v4/readiness.json)。v1–v3 为本轮准备过程的中间版本，保留；后续以 v4 为准，均没有执行 run。
- [240 条 assignments](../../reports/upgrade/a5-pilot20-preparation-20260921-v4/assignments.json)：20 tasks × B0–B3 × 3 repeats，种子 42/43/44 只组织顺序；每个 task/repeat 四变体连续配对，每个 variant 在每个位置各出现 15 次。所有 state 为 planned_not_started，没有拿计划行冒充结果行。
- 20 个本仓 PublicTask JSON，只有公开 issue/base commit 等 allowlist 字段；gold patch、test patch、hints、F2P/P2P 和 environment spec 在 private 区。每题另有独立 EvaluationSpec 引用，明确是仓库测试素材，**不是 H3 JSON 函数探针可直接接收的规格**。只可把公开 DTO 和未来审核过的公开 seed 交给 agent，不可挂载 preparation 根目录。
- [人工公开输入审查](../../configs/a5/pilot20-public-review.json)：20 条 problem_statement 已完整阅读，没有用目标 gold/test patch 选题或调方法。公开 issue 自带的建议原样保留，例如 `sympy-24152` 的四行代码建议、`django-13590` 的修复思路；不声称任务“完全无解题提示”。这与注入隐藏答案不同。启发式只标 3 条，完整判断以逐题说明为准。
- 20 份对应 base commit 的 LICENSE/COPYING 已抓取并记录原始 URL/hash，约 80.6 KB；这只是源码许可证证据，不补造上游数据卡没有声明的数据集许可。原始 parquet 为 1,119,540 bytes，含私有列，仅留在 preparation-private 目录并加入 gitignore。
- [宿主交接要求](../../reports/upgrade/a5-pilot20-preparation-20260921-v4/host-handoff.json)、[预算草案 JSON](../../reports/upgrade/a5-pilot20-preparation-20260921-v4/budget-request.DRAFT.json)、[artifact hash](../../reports/upgrade/a5-pilot20-preparation-20260921-v4/artifact-manifest.json)、[实现与规则 hash](../../reports/upgrade/a5-pilot20-preparation-20260921-v4/code-manifest.json)。没有生成真实执行脚本或自动解锁开关。

## 20 题是什么

来源为 [SWE-bench Lite](https://huggingface.co/datasets/princeton-nlp/SWE-bench_Lite)，revision 固定为 `6ec7bb89b9342f664a54a6e0a6ea6501d3437cc2`，原始 test split SHA256=`7a21f37b8bc179c7db5beeb14e88ac538ba283455c776e6b2535bbfb6e3551b4`。选取规则只读公开列，在五个预定 repo 的 2020 年及以后 PR 中按固定 hash 排序各取四题；未按结果/patch 长度/可修复性挑选。上游 `created_at` 是 PR 创建时间，不是 issue 创建/最后编辑、PR merge 或修复成功时间。

| 仓库 | 任务 ID（省略 repo 前缀） | 公开问题 |
|---|---|---|
| Django | 13265 / 15781 / 13590 / 13448 | migration 顺序、命令帮助 formatter、namedtuple range 查询、禁用 migration 的测试数据库 |
| SymPy | 20154 / 24152 / 20442 / 18532 | partitions 字典复用、TensorProduct 展开、单位转换、atoms 定义 |
| scikit-learn | 25747 / 25500 / 25638 / 25570 | FeatureUnion、校准器、nullable labels、零列 ColumnTransformer 的 pandas 互操作 |
| pytest | 8365 / 7432 / 9359 / 7220 | 用户名临时路径、skip 位置、assert 多打印源码、fixture 改 cwd 后的路径 |
| Sphinx | 10451 / 8721 / 8595 / 8713 | star args 文档、epub viewcode、空 `__all__`、napoleon other parameters |

scikit-learn 四题保守归入同一语义组，整体暂记 17 个组、5 个 repo；20 题不能作为 20 个完全独立问题声称显著性。配对描述仍按 task；今后推断性分析需按 repo/相关组处理。Django 数据库、pytest Windows/Python 版本及 sklearn 的 lightgbm 公开复现差异均记入审查，不在预检后悄悄换成容易题。环境失败保留原分母，若任务集合确需调整则另立版本。

公开 benchmark 可能已被模型见过，不能据此宣称模型预训练去污染。当前 agent 只在数据准备阶段阅读公开输入，不使用这些目标运行结果调策略；旧 synthetic/legacy/dev 仍不进入这 20 题。

## 历史池与待 harness 项目

同一来源中按固定规则锁定 20 条 2020 年之前的同仓来源候选：Django、SymPy、scikit-learn、pytest 各 5 条；Sphinx 没有符合时间规则的来源。它们是旧 issue/PR 材料，**不是已观测的 agent 轨迹或 validated MemoryRecord**。当前不生成伪造 procedure 成功记录，也不把历史来源的 gold/test_patch 假装为公开验证。

正式四变体实验还需要：补足并审核历史公开轨迹，实际验证来源，提取依赖并冻结同一 memory snapshot；固定 20 个公开 seed 和环境；让独立 grader 支持各仓测试并确认原始 bug；四变体在同一宿主 profile 上接线；核对全部 model starts、注入 bytes/hash 与 operation/attempt、失败/retry/费用账本。这些都列入 host-handoff，不修改正在同步的 harness。

当前 H3 函数探针 grader 不支持这批整仓任务。因此“预算获批”本身不会将当前候选包变成可执行 pilot；grader/环境、真实历史池及最终来源/分组清单必须同时就绪。本批仅固定选择、公开 DTO 和计划，不把 `reviewed=true`、空 memory 或脚本退出码当作运行验收。

## A5 预算授权与建池分账

候选方案为 DeepSeek Flash、thinking disabled；确切 model snapshot 与当次官方价目仍待宿主绑定。当前按用户图片提供的高峰、缓存未命中参考价计算：输入 2 元/百万 tokens、输出 8 元/百万 tokens；图片不是 provider 验价凭证。

- 240 个首次 task-runs，最多 1,440 个 model attempts；失败和内部 retry 都在每 run 6 次以内。
- 输入/输出上限 11.52M/2.88M，按上述参考价估算在线模型费用上限 **$6.912**，不是账单或已确认现价。
- 用户已授权正式 pilot 约 **50.000 元**；按参考价 240 个首跑的理论 token 上限为 46.080 元，每个 6-call task-run 按 0.192 元封顶，剩余部分是 pilot 运行余量。
- 记忆池建设独立计账，不从 pilot 预算扣除。当前固定 20 个历史来源、每个最多两次尝试，共 40 个 build/retry 计划，目标是 15–25 条实际验证合格的 MemoryRecord；失败、unknown、重试全部保留并计账。
- 本方案不含收费 builder/router/summary/verifier/grader。结构化抽取优先规则/人工；实际模型调用仍由 harness 统一网关执行。完整合同见 [A5-FUNDED-BUILD-v2](A5-FUNDED-BUILD-v1.md)。

运行前仍须由 harness 绑定确切 model snapshot、当前 provider 价目、全局/单 run CNY 限额和完整 usage ledger。240×600 秒是串行 agent 阶段最多 40 小时的容量上界，环境准备和独立 grader 耗时另算，并非实测运行时间。当前 authorized_amount=50.000 CNY、actual_spend=0、real_api_enabled=false。

## 验证与复现

已有环境：Python 3.11.15、PyArrow 24.0.0、Pydantic 2.13.4、pytest 8.4.2、Ruff 0.15.20；未安装新包。PyArrow 仅用于私有离线 intake，不成为 H4 插件依赖。新测试无 PyArrow 时会跳过 parquet round-trip；本机实际有 PyArrow，未跳过这些测试。

定向 **82 passed in 3.47s**，覆盖本批 8 个测试及 A5/H4 回归，见 [targeted.xml](../../reports/upgrade/a5-pilot20-verification-20260921/targeted.xml)。最终扩大离线回归 **230 passed in 63.84s**，见 [regression.xml](../../reports/upgrade/a5-pilot20-verification-20260921/regression.xml)；两组重叠，不相加。全仓 Ruff 通过。一次执行审批超时且未启动，按允许的一次重试成功；后续只测试本仓 fixtures。

测试证明：私有 patch/hints/F2P/P2P 改变不影响选题、PublicTask 或 assignments；重复 ID/base/issue 和来源 bytes 篡改拒绝；候选不足不凑数；240 分配唯一且平衡；不同工具/profile 拒绝；公开目录不含 fixture 私有 sentinel；无预算继承、无覆盖输出。真实包只读复核：**162 个 artifacts、5 个实现/规则 hash 全部一致，20 个 PublicTask 通过严格 decoder**。

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
& 'C:\Users\Administrator\.conda\envs\coding-harness\python.exe' scripts/prepare_a5_pilot20.py --source benchmarks/a5/pilot20-source-v1/private/test.parquet --lock configs/a5/pilot20-source-lock.json --output reports/upgrade/a5-pilot20-preparation-20260921-v4
& 'C:\Users\Administrator\.conda\envs\coding-harness\python.exe' -m pytest tests/test_a5_preparation.py tests/test_a5_contracts.py tests/test_a5_variants.py tests/test_a5_audit.py tests/test_harness_h4_adapter.py -q -o addopts='' -p no:cacheprovider --basetemp=traces/upgrade_a5_pilot20_20260921_02 --junitxml=reports/upgrade/a5-pilot20-verification-20260921/targeted.xml
```

上述是实际命令，复跑须更换新的 output/basetemp，原目录不能覆盖。只从不可变 URL重新下载原始 parquet/README，按 source-lock 校验后才可 intake；不要从可变 main 或其他 oracle/BM25 数据集替换。

扩大回归的精确命令：

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PATH='C:\Users\Administrator\.conda\envs\coding-harness;C:\Users\Administrator\.conda\envs\coding-harness\Scripts;' + $env:PATH
& 'C:\Users\Administrator\.conda\envs\coding-harness\python.exe' -m pytest tests --ignore=tests/test_cli.py --ignore=tests/test_llm_ablation.py --ignore=tests/test_external_baselines.py --ignore=tests/test_phase7_benchmark.py -q -o addopts='' -p no:cacheprovider --basetemp=traces/upgrade_a5_pilot20_regression_20260921_01 --junitxml=reports/upgrade/a5-pilot20-verification-20260921/regression.xml
```

范围排除了会写默认报告的旧 CLI、外部 baseline 和全量 benchmark，故不称全套测试通过。H4 adapter、fixture 生成器和测试的 hash 与原 H4 review 一致；没有因准备真实数据改写旧插件。

本轮新增 `experiments/preparation.py`、`scripts/prepare_a5_pilot20.py`、8 项测试及两个来源/审查 config；新增准备合同、本文和来源说明，更新 README、A5-PLAN、PUBLIC-API 与私有原始数据的 gitignore。无可用 Git 元数据，未 commit/push。[累计源码 diff](../../reports/upgrade/a5-pilot20-review-20260921-v2/changes.diff)与[hash 清单](../../reports/upgrade/a5-pilot20-review-20260921-v2/manifest.json)对照最初的 allowlist snapshot 生成，含 TP/H4/A5 前期改动，不能冒充本轮专属 diff。文档和私有原始数据不全在该旧 snapshot allowlist，分别由当前文件及准备包 manifest 审阅。

本轮停止点：**等待用户单独批准 A5 预算，同时等待明确列出的数据/宿主预检条件；不自动执行正式 pilot。**

本轮状态更新：预算授权已获得。下一停止点是 harness 整仓 grader、模型/价目绑定、host ledger 和历史任务的公开基线预检；这些通过后先运行固定的 20 个 build jobs（最多 40 个 attempts），再冻结 MemoryRecord snapshot，之后才进入正式 pilot。没有 host receipt 时不把建池任务记作轨迹或记忆。
