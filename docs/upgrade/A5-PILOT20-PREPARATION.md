# A5 20 题 pilot 前置合同 v1

2026-09-21，先于本批数据选择及实现。用户授权以 20 题为目标准备前置工作；后续已授权约 50 CNY 并支持必要的付费建池。harness 同步期间不做依赖对方的运行，正式 pilot 仍需宿主预检和唯一预算账本；本准备包没有付费调用或自动启动器，也不沿用 harness 其他实验的预算授权。

## 不变的研究合同

沿用 A5-PLAN 的 E-A1 B0–B3、同池 raw-history lexical 排名、top-3/最多 2 条/4096 bytes、cold frozen memory、相同 runtime/profile、6 model attempts/48k input/12k output/600s/30 tools/retry=1。20 个 unique tasks × 4 variants × 3 repeats，共 240 个计划 task-runs。首 run attempt 决定主要结果；missing/fail/invalid_env/degraded 不删；重跑另记并计费。主指标/成本/paired task differences 不改，不承诺收益或显著性。

## 本批数据选择规则

本地现有任务主要为已开发/已知结果的 synthetic legacy 和 dev fixtures，不能重新标 heldout。优先从公开的 `princeton-nlp/SWE-bench_Lite` 取得不可变 revision 的真实 issue/base-commit 元数据和评测材料，记录下载来源及原始 bytes SHA256，不运行其中代码。此处只是候选准备，不宣称完整 SWE-bench 成绩或模型预训练去污染。

目标为 5 个 Python 仓库各 4 题：django/django、sympy/sympy、scikit-learn/scikit-learn、pytest-dev/pytest、sphinx-doc/sphinx。目标创建时间不早于 2020-01-01 UTC，issue 长度适合现有 PublicTask，instance_id/base_commit 唯一。在各仓内按 SHA256(`a5-pilot20-v1:` + instance_id) 排序取前 4，不看 gold patch、测试结果、修复长度、变体输出选题。资格不够则如实缺额，不替换为 synthetic 或事后按可修复性换题。先保存完整筛选台账再导出。每题的公开材料采用 problem_statement 与 base_commit，不使用 hints_text、目标 patch、test_patch 或 FAIL_TO_PASS/PASS_TO_PASS 作为策略输入。

另按同仓历史时间准备 memory_build 来源候选：2020-01-01 之前且早于全部目标、与目标不重复，按发生时间/ID 选择每仓最多 1 条。没有可验证的历史执行证据时不得标 validated；无合格历史来源就保留缺口。开发中的 A5 dev 和 H4/H5 任务继续排除主分母。不用目标答案建立 procedure、不把历史目标私有测试转换为“公开验证”。

## 分离与冻结层次

原始 benchmark 行含私有评测字段，仅写 preparation-private 区，不挂载给策略。逐题 PublicTask 导出只采用 allowlist。独立 EvaluationSpec 保存私有文件引用，不把 test lists、patch 或 hidden text 放进公开 task、schedule 或 context。SWE-bench pytest/environment material 与当前 harness H3 JSON 函数 grader 不等价；先提供独立数据规格和宿主要求，运行/适配暂缓，不假装 H3 已支持。

这轮冻结候选 ID、原始来源版本、公开 DTO 和待执行 assignment schedule；最终 dataset/memory/runtime 的 runnable 冻结须通过出处/license、人工公开性/重复组审查、公开 seed checkout、历史 validation 和宿主无模型环境预检。每项区分通过、待审与待 harness；缺证据保持未就绪，不能通过 `reviewed=true` 或空记忆假装完成。A5 原来的 4 场景 smoke 结果不修改。

## 交付包与停止点

1. 来源锁定与 intake：固定下载源、可重复选择器、20 候选的公开/私有分离、排除/待审台账。
2. pilot 准备：固定 240 assignments、稳定的配对随机顺序、来源/配置 hash、fail-closed readiness、host handoff requirements、预算申请草案（金额尚未批准）。
3. 离线验证：选择不读答案、private sentinel、重复/篡改/未审批拒绝、schedule 完整、输入 hash 可复核；生成审阅报告和差异记录。

成功信号是可复核的真实候选材料、完全分离的公开输入、诚实的阻塞清单和零模型调用。失败信号包括按答案选题、暴露 test patch、将未知验证标通过、消耗其他实验额度、自动运行 pilot。完成上述准备后停下，向用户报告 A5 预算待批及待 harness 的明确项目，不触发任何真实执行。
