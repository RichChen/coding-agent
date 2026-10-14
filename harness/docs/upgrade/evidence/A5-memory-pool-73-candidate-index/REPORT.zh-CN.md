# A5 Memory Pool S0 Candidate Index Report

日期：2026-09-22。attempt：A5-memory-pool-73-candidate-index。

## 本轮做了什么

- 建立 20 行 candidate-index.jsonl，核对 repo/base/archive/tree/transport/collection/baseline 与旧失败引用。
- 按合同重算状态：**不继承** 66/67 的 grader-ready，不把 71/72 的 11/20 当验收基线。
- 选定 6 个 S1 smoke 候选并记录计划；**未执行** smoke/build，未产生 trajectory，未付费。
- model_calls=0，paid=false，shared-gate B0–B3 标为 ixture_only。

## 计数（诚实）

| 项 | 数量 |
|---|---|
| 索引 source | 20 |
| environment baseline_ready | 15 |
| invalid_env（保留） | 5 |
| 合同下 grader_ready | 0 |
| S1 smoke 已执行 | 0 / 6 planned |
| validated MemoryRecord | 0 |
| candidate MemoryRecord | 0 |

## S1 选定（未执行）

- django__django-10914
- sympy__sympy-11400
- scikit-learn__scikit-learn-10297
- pytest-dev__pytest-5103
- django__django-10924
- sympy__sympy-11870

覆盖 repo family：django、sympy、scikit-learn、pytest-dev。

## 最关键缺口

1. 尚无任何真实公开 trajectory → 无法产生 MemoryRecord。
2. 独立 memory-build 预算与用户付费授权尚未落地到本 attempt。
3. smoke/validation CLI 需在后续执行前确认真实存在。
4. 5 个 invalid_env 来源需单独诊断，但不阻塞先对其他来源做小池。

## 需要用户另行决定

- paid scope：是否授权对上述 6 个 source 启动 S1 smoke/build，以及 CNY 硬上限 reservation。
- 可选研究升级：24 题全量预检、20×4×3 pilot、统计显著性、全量 full-repo grader calibration。
