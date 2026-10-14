# A5 Memory Pool 公开交接（轻量合同 v2）

日期：2026-09-22。  
合同：`docs/upgrade/A5-PRE-MEMORY-CURSOR-CONTRACT.zh-CN.md`

## 状态摘要

| 项 | 值 |
|---|---|
| S0 | `A5-memory-pool-73-candidate-index` |
| S1 | `A5-memory-pool-75-s1-smoke` |
| **S2** | **`A5-memory-pool-76-s2`** |
| **validated** | **11** |
| candidate | 0（已审查升格或失败留账） |
| failed retained | 4 |
| blocked（invalid_env，未付费） | 5 |
| validation scope | 公开独立 smoke receipt + 规则 provenance review |
| private full-repo grader | **未跑**（诚实标注） |
| paid / pilot | true / 未启动 |

## Validated（11）

- `django__django-10914`
- `django__django-10924`
- `django__django-11039`
- `sympy__sympy-11400`
- `sympy__sympy-12171`
- `scikit-learn__scikit-learn-10297`
- `scikit-learn__scikit-learn-10949`
- `scikit-learn__scikit-learn-11040`
- `scikit-learn__scikit-learn-11281`
- `pytest-dev__pytest-5103`
- `pytest-dev__pytest-5221`

## Failed retained（不升格）

- `sympy__sympy-11870`（S1）
- `sympy__sympy-11897`
- `scikit-learn__scikit-learn-10508`
- `pytest-dev__pytest-5227`（含一次 allowlist 复验仍失败）

## Evidence

- `docs/upgrade/evidence/A5-memory-pool-76-s2/`
  - `validated-memory-records.jsonl`
  - `failure-ledger.jsonl`
  - `s2-status.json` / `REPORT.zh-CN.md`
  - `builds/`、`provenance-review-*`

## 合同边界（已遵守）

- 未伪造轨迹；失败未因“不够 15”升格
- 未对 5 个 invalid_env blocked 源付费
- 未要求未采用源先做 full-repo grader calibration
- 15 不是承诺；当前 **11** 条可用轻量池，诚实停止

## 缺口 / 可选下一步

- 未达 15；剩余失败需新策略才可再试
- 若需要私有 F2P/full-repo grader 级 validated，须另立授权与 attempt
- S3 研究升级（全量预检 / 20×4×3 pilot / 显著性）仍为可选项，非前置
