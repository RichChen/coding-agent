# A5 Memory Pool S2 Report

日期：2026-09-22T11:41:15.705111+00:00
attempt：`A5-memory-pool-76-s2`

## 结果（诚实）

- **validated = 11**（公开独立 validation + 规则 provenance review；未跑私有 full-repo grader）
- candidate = 0（已审查者升格或失败留账）
- failed retained = 4
- blocked (invalid_env, 未付费) = 5
- S2 builds model_calls = 223, spent_cny = 2.483

## Validated

- `django__django-10914`
- `django__django-10924`
- `sympy__sympy-11400`
- `scikit-learn__scikit-learn-10297`
- `pytest-dev__pytest-5103`
- `django__django-11039`
- `sympy__sympy-12171`
- `scikit-learn__scikit-learn-10949`
- `scikit-learn__scikit-learn-11040`
- `pytest-dev__pytest-5221`
- `scikit-learn__scikit-learn-11281`

## Failed retained

- `sympy__sympy-11870`: no_candidate_changes_budget_exhausted_no_edits
- `sympy__sympy-11897`: no_candidate_changes_budget_exhausted_no_edits
- `scikit-learn__scikit-learn-10508`: edits_recorded_but_empty_delta
- `pytest-dev__pytest-5227`: unassigned_path_then_reverify_still_failed

## 合同遵守

- 未伪造/倒填轨迹；失败未因数量不足升格
- 未对 blocked invalid_env 源付费强跑
- 未要求未采用源先做 full-repo grader calibration
- 15 不是承诺；当前 11 条可用轻量 validated 池，诚实停止

## 缺口

- 未达 15；剩余失败需新策略才可再试
- validated 范围为公开 smoke receipt，不是私有 F2P grader 证明
