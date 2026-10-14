# CHECKPOINT-P2 附件：第 4 节第 2、3 项和跨仓库引用的完整清单

由 `CHECKPOINT-P2.md` 引用。对象是 monorepo `D:\crq\src\coding-agent-mono` 的 HEAD `f22a261` 和全部历史。只列路径、计数和行号，不含文件内容。

## A. 第 2 项：历史中出现过 `FAIL_TO_PASS`、`test_patch`、`"patch":` 的路径

共 129 个路径，其中 107 个在 HEAD 里。不带 `harness/`、`agent/` 前缀的路径来自子树并入前的原始提交（它们在 monorepo 里对应带前缀的同名文件，或者已经从原仓库 HEAD 移除）。H 表示在 HEAD 里。

| HEAD | 路径 | 字段 |
| --- | --- | --- |
| H | `agent/benchmarks/a5/pilot20-source-v1/README.upstream.md` | `FAIL_TO_PASS`、`test_patch` |
| H | `agent/configs/a5/canonical-handoff.json` | `FAIL_TO_PASS`、`test_patch` |
| H | `agent/configs/a5/lightweight-memory-import.schema.json` | `test_patch` |
| H | `agent/docs/upgrade/A5-PILOT20-PREPARATION.md` | `FAIL_TO_PASS`、`test_patch` |
| H | `agent/docs/upgrade/A5-PILOT20-STATUS.md` | `test_patch` |
| H | `agent/reposkill_agent/core/context_expansion.py` | `"patch":` |
| H | `agent/reposkill_agent/eval/graph_runner.py` | `"patch":` |
| H | `agent/reposkill_agent/experiments/funding.py` | `FAIL_TO_PASS`、`test_patch` |
| H | `agent/reposkill_agent/experiments/preparation.py` | `FAIL_TO_PASS`、`test_patch` |
| H | `agent/reposkill_agent/memory/lightweight_snapshot.py` | `FAIL_TO_PASS`、`test_patch` |
| H | `agent/scripts/build_memory_cards.py` | `FAIL_TO_PASS`、`test_patch` |
| H | `agent/tests/test_a5_funding.py` | `test_patch` |
| H | `agent/tests/test_a5_preparation.py` | `"patch":`、`FAIL_TO_PASS`、`test_patch` |
| H | `agent/tests/test_event_extract.py` | `FAIL_TO_PASS`、`test_patch` |
| H | `agent/tests/test_memory_cards.py` | `FAIL_TO_PASS`、`test_patch` |
| H | `agent/tests/test_memory_cards_v3.py` | `FAIL_TO_PASS`、`test_patch` |
| H | `agent/tests/test_memory_cards_v5.py` | `FAIL_TO_PASS` |
|  | `docs/sprint/A5-MAIN-FREEZE.md` | `FAIL_TO_PASS`、`test_patch` |
|  | `docs/sprint/CHECKPOINT-6.md` | `test_patch` |
|  | `docs/sprint/PROGRESS.md` | `FAIL_TO_PASS` |
|  | `docs/sprint/memory-source-runs.json` | `test_patch` |
| H | `harness/docs/archive/SOLID-D1-POLISH-EXECUTION.zh-CN.md` | `test_patch` |
| H | `harness/docs/archive/SOLID-D1-SCAFFOLD-EXECUTION.zh-CN.md` | `FAIL_TO_PASS`、`test_patch` |
| H | `harness/docs/archive/SOLID-D1-SWEBENCH-EXECUTION.zh-CN.md` | `FAIL_TO_PASS`、`test_patch` |
| H | `harness/docs/changes/SOLID-D1-POLISH-CLOSEOUT.zh-CN.md` | `FAIL_TO_PASS`、`test_patch` |
| H | `harness/docs/changes/SOLID-D1-SWEBENCH-CLOSEOUT.zh-CN.md` | `FAIL_TO_PASS`、`test_patch` |
| H | `harness/docs/publish/AUDIT-P1.zh-CN.md` | `FAIL_TO_PASS` |
| H | `harness/docs/publish/CHECKPOINT-P1.md` | `"patch":`、`FAIL_TO_PASS`、`test_patch` |
| H | `harness/docs/publish/PUBLISH-CONTRACT.zh-CN.md` | `"patch":`、`FAIL_TO_PASS`、`test_patch` |
| H | `harness/docs/sprint/A5-MAIN-FREEZE.md` | `FAIL_TO_PASS`、`test_patch` |
| H | `harness/docs/sprint/AUDIT-3-CORRECTION.zh-CN.md` | `test_patch` |
| H | `harness/docs/sprint/CHECKPOINT-6.md` | `test_patch` |
| H | `harness/docs/sprint/CHECKPOINT-A6-1.md` | `FAIL_TO_PASS` |
| H | `harness/docs/sprint/HARNESS-CAPABILITY-SPRINT.zh-CN.md` | `FAIL_TO_PASS` |
| H | `harness/docs/sprint/HARNESS-SPRINT-6C-FIX.zh-CN.md` | `FAIL_TO_PASS`、`test_patch` |
| H | `harness/docs/sprint/MEMORY-SOURCE-EXPANSION.md` | `FAIL_TO_PASS`、`test_patch` |
| H | `harness/docs/sprint/PROGRESS.md` | `FAIL_TO_PASS` |
| H | `harness/docs/sprint/a6-attempts.json` | `test_patch` |
| H | `harness/docs/sprint/memory-source-runs.json` | `test_patch` |
| H | `harness/docs/upgrade/evidence/A5-harness-preflight-10-input-gate/inputs.json` | `test_patch` |
| H | `harness/docs/upgrade/evidence/A5-harness-preflight-25g-repo-baseline-sympy20154/receipts.json` | `test_patch` |
| H | `harness/docs/upgrade/evidence/A5-harness-preflight-25g-repo-baseline-sympy20154/tasks/sympy__sympy-20154/receipt.json` | `test_patch` |
| H | `harness/docs/upgrade/evidence/A5-harness-preflight-25k-repo-baseline-sphinx8595/receipts.json` | `test_patch` |
| H | `harness/docs/upgrade/evidence/A5-harness-preflight-25k-repo-baseline-sphinx8595/tasks/sphinx-doc__sphinx-8595/receipt.json` | `test_patch` |
| H | `harness/docs/upgrade/evidence/A5-harness-preflight-25l-repo-baseline-sphinx8595/receipts.json` | `test_patch` |
| H | `harness/docs/upgrade/evidence/A5-harness-preflight-25l-repo-baseline-sphinx8595/tasks/sphinx-doc__sphinx-8595/receipt.json` | `test_patch` |
| H | `harness/docs/upgrade/evidence/A5-harness-preflight-27-repo-baseline/tasks/sphinx-doc__sphinx-10451/receipt.json` | `test_patch` |
| H | `harness/docs/upgrade/evidence/A5-harness-preflight-27-repo-baseline/tasks/sphinx-doc__sphinx-8595/receipt.json` | `test_patch` |
| H | `harness/docs/upgrade/evidence/A5-harness-preflight-27-repo-baseline/tasks/sphinx-doc__sphinx-8713/receipt.json` | `test_patch` |
| H | `harness/docs/upgrade/evidence/A5-harness-preflight-27-repo-baseline/tasks/sphinx-doc__sphinx-8721/receipt.json` | `test_patch` |
| H | `harness/docs/upgrade/evidence/A5-harness-preflight-33-sklearn-compiler/receipts.json` | `test_patch` |
| H | `harness/docs/upgrade/evidence/A5-harness-preflight-33-sklearn-compiler/tasks/scikit-learn__scikit-learn-25500/receipt.json` | `test_patch` |
| H | `harness/docs/upgrade/evidence/A5-harness-preflight-33-sklearn-compiler/tasks/scikit-learn__scikit-learn-25747/receipt.json` | `test_patch` |
| H | `harness/docs/upgrade/evidence/A5-harness-preflight-34-sklearn-https/receipts.json` | `test_patch` |
| H | `harness/docs/upgrade/evidence/A5-harness-preflight-34-sklearn-https/tasks/scikit-learn__scikit-learn-25500/receipt.json` | `test_patch` |
| H | `harness/docs/upgrade/evidence/A5-harness-preflight-34-sklearn-https/tasks/scikit-learn__scikit-learn-25570/receipt.json` | `test_patch` |
| H | `harness/docs/upgrade/evidence/A5-harness-preflight-34-sklearn-https/tasks/scikit-learn__scikit-learn-25638/receipt.json` | `test_patch` |
| H | `harness/docs/upgrade/evidence/A5-harness-preflight-34-sklearn-https/tasks/scikit-learn__scikit-learn-25747/receipt.json` | `test_patch` |
| H | `harness/docs/upgrade/evidence/A5-harness-preflight-35-sphinx-test-files/tasks/sphinx-doc__sphinx-10451/receipt.json` | `test_patch` |
| H | `harness/docs/upgrade/evidence/A5-harness-preflight-35-sphinx-test-files/tasks/sphinx-doc__sphinx-8595/receipt.json` | `test_patch` |
| H | `harness/docs/upgrade/evidence/A5-harness-preflight-35-sphinx-test-files/tasks/sphinx-doc__sphinx-8713/receipt.json` | `test_patch` |
| H | `harness/docs/upgrade/evidence/A5-harness-preflight-35-sphinx-test-files/tasks/sphinx-doc__sphinx-8721/receipt.json` | `test_patch` |
| H | `harness/docs/upgrade/evidence/A5-harness-preflight-36-repo-compat/tasks/sphinx-doc__sphinx-8721/receipt.json` | `test_patch` |
| H | `harness/docs/upgrade/evidence/A5-harness-preflight-38-sklearn-snapshot-smoke/receipts.json` | `test_patch` |
| H | `harness/docs/upgrade/evidence/A5-harness-preflight-38-sklearn-snapshot-smoke/tasks/scikit-learn__scikit-learn-25747/receipt.json` | `test_patch` |
| H | `harness/docs/upgrade/evidence/A5-harness-preflight-40-sklearn-full/receipts.json` | `test_patch` |
| H | `harness/docs/upgrade/evidence/A5-harness-preflight-40-sklearn-full/tasks/scikit-learn__scikit-learn-10297/receipt.json` | `test_patch` |
| H | `harness/docs/upgrade/evidence/A5-harness-preflight-40-sklearn-full/tasks/scikit-learn__scikit-learn-25500/receipt.json` | `test_patch` |
| H | `harness/docs/upgrade/evidence/A5-harness-preflight-40-sklearn-full/tasks/scikit-learn__scikit-learn-25570/receipt.json` | `test_patch` |
| H | `harness/docs/upgrade/evidence/A5-harness-preflight-40-sklearn-full/tasks/scikit-learn__scikit-learn-25638/receipt.json` | `test_patch` |
| H | `harness/docs/upgrade/evidence/A5-harness-preflight-48-django-contract-resolution/contract-resolution.json` | `test_patch` |
| H | `harness/docs/upgrade/evidence/A5-harness-preflight-57-remaining16-baseline/tasks/pytest-dev__pytest-5221/receipt.json` | `test_patch` |
| H | `harness/docs/upgrade/evidence/A5-harness-preflight-57-remaining16-baseline/tasks/pytest-dev__pytest-5227/receipt.json` | `test_patch` |
| H | `harness/docs/upgrade/evidence/A5-harness-preflight-57-remaining16-baseline/tasks/pytest-dev__pytest-5413/receipt.json` | `test_patch` |
| H | `harness/docs/upgrade/evidence/A5-harness-preflight-57-remaining16-baseline/tasks/pytest-dev__pytest-5495/receipt.json` | `test_patch` |
| H | `harness/docs/upgrade/evidence/A5-harness-preflight-62-history-baseline-retry/tasks/pytest-dev__pytest-5103/receipt.json` | `test_patch` |
| H | `harness/docs/upgrade/evidence/A5-real240-77-harness-preflight/memory-consumption-contract.json` | `FAIL_TO_PASS`、`test_patch` |
| H | `harness/docs/upgrade/evidence/A5-real240-77-harness-preflight/public-boundary-audit.json` | `FAIL_TO_PASS`、`test_patch` |
| H | `harness/reports/examples/swebench_lite_real.md` | `FAIL_TO_PASS`、`test_patch` |
| H | `harness/reports/examples/tmp_requests_2674_log.json` | `FAIL_TO_PASS` |
| H | `harness/reports/examples/tmp_requests_863_log.json` | `FAIL_TO_PASS` |
| H | `harness/scripts/a5_memory_provenance_review.py` | `FAIL_TO_PASS`、`test_patch` |
| H | `harness/scripts/a5_memory_source_smoke.py` | `test_patch` |
| H | `harness/scripts/audit/audit_b0_deltas.py` | `FAIL_TO_PASS`、`test_patch` |
| H | `harness/scripts/audit/audit_v6.py` | `FAIL_TO_PASS`、`test_patch` |
| H | `harness/scripts/audit_a5_host_preflight.py` | `FAIL_TO_PASS`、`test_patch` |
| H | `harness/scripts/audit_a5_repo_baseline.py` | `FAIL_TO_PASS` |
| H | `harness/scripts/build_a6_attempts.py` | `FAIL_TO_PASS`、`test_patch` |
| H | `harness/scripts/build_clean_baseline.py` | `test_patch` |
| H | `harness/scripts/build_swebench_lite_subset.py` | `FAIL_TO_PASS`、`test_patch` |
| H | `harness/scripts/calibrate_pilot_image_grader.py` | `FAIL_TO_PASS`、`test_patch` |
| H | `harness/scripts/diagnose_pytest7432_ids.py` | `FAIL_TO_PASS` |
| H | `harness/scripts/preflight_a5_pytest.py` | `FAIL_TO_PASS`、`test_patch` |
| H | `harness/scripts/preflight_a5_repo_baseline.py` | `FAIL_TO_PASS`、`test_patch` |
| H | `harness/scripts/recheck_a5_repo_baseline.py` | `FAIL_TO_PASS`、`test_patch` |
| H | `harness/scripts/run_a5_main.py` | `FAIL_TO_PASS`、`test_patch` |
| H | `harness/scripts/run_a5_real.py` | `FAIL_TO_PASS` |
| H | `harness/scripts/run_swe_task.py` | `FAIL_TO_PASS`、`test_patch` |
| H | `harness/scripts/select_main_targets.py` | `"patch":`、`FAIL_TO_PASS`、`test_patch` |
| H | `harness/scripts/select_swebench_instances.py` | `FAIL_TO_PASS` |
| H | `harness/scripts/sprint2_calibrate.py` | `FAIL_TO_PASS`、`test_patch` |
| H | `harness/scripts/sprint4_write_b0_results.py` | `test_patch` |
| H | `harness/scripts/sprint5_prepare_main.py` | `FAIL_TO_PASS`、`test_patch` |
| H | `harness/scripts/sprint5_scan_official.py` | `test_patch` |
| H | `harness/scripts/sprint6_void_r2.py` | `FAIL_TO_PASS`、`test_patch` |
| H | `harness/src/eval/a5_memory_snapshot.py` | `FAIL_TO_PASS`、`test_patch` |
| H | `harness/tests/test_a5_repo_baseline.py` | `test_patch` |
| H | `harness/tests/test_build_a6_attempts.py` | `"patch":`、`FAIL_TO_PASS`、`test_patch` |
| H | `harness/tests/test_no_silent_fallback.py` | `"patch":`、`test_patch` |
| H | `harness/tests/test_run_a5_main.py` | `"patch":`、`FAIL_TO_PASS`、`test_patch` |
| H | `harness/tests/test_sprint6_predict_injection.py` | `"patch":` |
|  | `scripts/build_a6_attempts.py` | `FAIL_TO_PASS`、`test_patch` |
|  | `scripts/build_clean_baseline.py` | `test_patch` |
|  | `scripts/build_memory_cards.py` | `FAIL_TO_PASS`、`test_patch` |
|  | `scripts/preflight_a5_repo_baseline.py` | `FAIL_TO_PASS`、`test_patch` |
|  | `scripts/run_a5_main.py` | `FAIL_TO_PASS`、`test_patch` |
|  | `scripts/run_swe_task.py` | `FAIL_TO_PASS`、`test_patch` |
|  | `scripts/select_main_targets.py` | `"patch":`、`FAIL_TO_PASS`、`test_patch` |
|  | `scripts/sprint4_write_b0_results.py` | `test_patch` |
|  | `scripts/sprint5_prepare_main.py` | `FAIL_TO_PASS`、`test_patch` |
|  | `swebench_candidates.jsonl` | `FAIL_TO_PASS` |
|  | `swebench_candidates_short.jsonl` | `FAIL_TO_PASS` |
|  | `tests/test_build_a6_attempts.py` | `"patch":`、`FAIL_TO_PASS`、`test_patch` |
|  | `tests/test_event_extract.py` | `FAIL_TO_PASS`、`test_patch` |
|  | `tests/test_memory_cards.py` | `FAIL_TO_PASS`、`test_patch` |
|  | `tests/test_memory_cards_v3.py` | `FAIL_TO_PASS`、`test_patch` |
|  | `tests/test_run_a5_main.py` | `"patch":`、`FAIL_TO_PASS`、`test_patch` |
|  | `tmp_requests_2674.jsonl` | `FAIL_TO_PASS` |
|  | `tmp_requests_863.jsonl` | `FAIL_TO_PASS` |

## B. 第 3 项：HEAD 中含本机信息的被跟踪文件

### `D:\crq`：744 个文件，4496 处

```
   14  agent/benchmarks/a5/memory-cards-v4.jsonl
   14  agent/benchmarks/a5/memory-cards-v5.jsonl
   70  agent/benchmarks/a5/memory-cards-v6.jsonl
   11  agent/configs/a5/canonical-handoff.json
    5  agent/configs/a5/pilot20-harness-consumption-manifest.json
    1  agent/docs/PROJECT-HISTORY.zh-CN.md
    2  agent/docs/archive/SESSION-HANDOFF.zh-CN.md
    9  agent/docs/memory-v2/DIAGNOSIS-AND-LITERATURE.zh-CN.md
    5  agent/docs/sprint/AGENT-MEMORY-2.zh-CN.md
    8  agent/docs/sprint/AGENT-MEMORY-3.zh-CN.md
    2  agent/docs/sprint/AGENT-MEMORY-4.zh-CN.md
    3  agent/docs/sprint/AGENT-MEMORY-5.zh-CN.md
    3  agent/docs/sprint/AGENT-MEMORY-7-CLOSEOUT.zh-CN.md
    3  agent/docs/sprint/AGENT-MEMORY-REBUILD.zh-CN.md
    1  agent/docs/sprint/CHECKPOINT-4.md
    6  agent/docs/sprint/CHECKPOINT-A6-4.md
   14  agent/docs/sprint/DEV-LOO-SELECTION.md
    1  agent/docs/sprint/MEMORY-INVENTORY.md
    1  agent/docs/sprint/PILOT-SELECTION-V4.md
    3  agent/docs/sprint/PROGRESS.md
   14  agent/docs/sprint/V4-CARDS.md
    1  agent/docs/upgrade/01_coding-harness_总修改目标_v1.0.md
    1  agent/docs/upgrade/02_coding-agent_总修改目标_v1.0.md
    5  agent/docs/upgrade/A5-CANONICAL-HANDOFF-RESOLUTION.md
    1  agent/docs/upgrade/IMPLEMENTATION-PLAN.md
    3  agent/docs/upgrade/VERIFICATION.md
    1  agent/docs/upgrade/planning-source-manifest.json
    1  agent/docs/upgrade/tasks/TP01-PUBLIC-BOUNDARY.md
    1  agent/docs/upgrade/tasks/TP02-EVIDENCE-LOCATOR.md
    1  agent/docs/upgrade/tasks/TP03-MEMORY-PROVENANCE.md
    1  agent/docs/upgrade/tasks/TP04-MEMORY-VALIDITY.md
    1  agent/reports/external_baselines/20260703_090321/reports/vanilla_deepseek_inv_api_tax_01.json
    1  agent/reports/external_baselines/20260703_090321/reports/vanilla_deepseek_inv_api_tax_holdout_01.json
    1  agent/reports/external_baselines/20260703_090321/reports/vanilla_deepseek_inv_rename_01.json
    3  agent/reports/external_baselines/20260703_090321/summary.json
    5  agent/scripts/build_memory_cards_v4.py
    1  agent/scripts/dev_loo_v4.py
    1  agent/scripts/dev_time_selection.py
    2  agent/scripts/pilot_selection_v4.py
    2  agent/scripts/posthoc_a6_anchor.py
    2  agent/tests/test_event_extract.py
    1  agent/tests/test_lightweight_snapshot.py
    2  agent/tests/test_memory_cards.py
    2  agent/tests/test_memory_cards_v3.py
    1  agent/tests/test_memory_cards_v5.py
    2  harness/configs/a5/model-price-binding.json
    2  harness/configs/a5/pilot20-harness-manifest.json
   14  harness/configs/sprint/dev-tasks.yaml
   39  harness/configs/sprint/pilot-tasks.yaml
    1  harness/docs/archive/DEMO-SCRIPT.zh-CN.md
    2  harness/docs/archive/SOLID-D1-REWORK-EXECUTION.zh-CN.md
    3  harness/docs/archive/SOLID-D1-SCAFFOLD-EXECUTION.zh-CN.md
    2  harness/docs/archive/SOLID-D2-DEMO-EXECUTION.zh-CN.md
    1  harness/docs/archive/SOLID-D2-REMAINING-EXECUTION.zh-CN.md
    2  harness/docs/changes/SOLID-D1-REWORK-CLOSEOUT.zh-CN.md
    3  harness/docs/publish/CHECKPOINT-P1-LOCAL-INFO.md
    7  harness/docs/publish/CHECKPOINT-P1.md
    4  harness/docs/publish/PUBLISH-CONTRACT.zh-CN.md
    7  harness/docs/publish/PUBLISH-START-PROMPTS.zh-CN.md
   12  harness/docs/sprint/A6-R-START-PROMPTS.zh-CN.md
    1  harness/docs/sprint/AUDIT-A6-3.zh-CN.md
    1  harness/docs/sprint/CHECKPOINT-7.md
    3  harness/docs/sprint/HARNESS-CAPABILITY-SPRINT.zh-CN.md
    2  harness/docs/sprint/HARNESS-SPRINT-2.zh-CN.md
    6  harness/docs/sprint/HARNESS-SPRINT-3.zh-CN.md
    2  harness/docs/sprint/HARNESS-SPRINT-5.zh-CN.md
    2  harness/docs/sprint/HARNESS-SPRINT-7-CLOSEOUT.zh-CN.md
    1  harness/docs/sprint/PROGRESS.md
    2  harness/docs/sprint/R4-START-PROMPTS.zh-CN.md
    1  harness/docs/sprint/b2-predicted-injection.json
   42  harness/docs/sprint/memory-source-runs.json
    1  harness/docs/upgrade/01_coding-harness_总修改目标_v1.0.md
    1  harness/docs/upgrade/02_coding-agent_总修改目标_v1.0.md
    3  harness/docs/upgrade/A5-HARNESS-GATE.zh-CN.md
    1  harness/docs/upgrade/A5-HOST-PREFLIGHT-24-CONTRACT.md
    1  harness/docs/upgrade/A5-PRE-MEMORY-CURSOR-PROMPT.zh-CN.md
    1  harness/docs/upgrade/A5-REAL240-HARNESS-CONTRACT.zh-CN.md
    1  harness/docs/upgrade/A5-REAL240-HARNESS-PROMPT.zh-CN.md
   11  harness/docs/upgrade/BASELINE-EVIDENCE.md
    1  harness/docs/upgrade/H5-INTEROP.zh-CN.md
    3  harness/docs/upgrade/IMPLEMENTATION-PLAN.md
    1  harness/docs/upgrade/R2-LITE-TRUE-SUMMARY.zh-CN.md
    4  harness/docs/upgrade/TASK-PACKAGES.md
    2  harness/docs/upgrade/evidence/A5-agent-canary-authorization-20260924-harness-attempt2/canary-preflight.json
    3  harness/docs/upgrade/evidence/A5-agent-canary-authorization-20260924-harness-attempt3/workspace-binding.json
    3  harness/docs/upgrade/evidence/A5-agent-canary-authorization-20260924-harness/canary-scope-receipt.json
  156  harness/docs/upgrade/evidence/A5-h3-dual-end-review-20260923-01/h3-dual-end-review.json
    1  harness/docs/upgrade/evidence/A5-h3-dual-end-review-20260923-01/matrix-coverage-recheck.json
    4  harness/docs/upgrade/evidence/A5-h3-dual-end-review-20260923-01/snapshot-recheck.json
  152  harness/docs/upgrade/evidence/A5-h3-dual-end-review-20260923-01/target-evidence-recheck.json
  157  harness/docs/upgrade/evidence/A5-h3-dual-end-review-20260923-02/h3-dual-end-review.json
    1  harness/docs/upgrade/evidence/A5-h3-dual-end-review-20260923-02/matrix-coverage-recheck.json
    4  harness/docs/upgrade/evidence/A5-h3-dual-end-review-20260923-02/snapshot-recheck.json
  152  harness/docs/upgrade/evidence/A5-h3-dual-end-review-20260923-02/target-evidence-recheck.json
  161  harness/docs/upgrade/evidence/A5-h3-dual-end-review-20260923-03/h3-dual-end-review.json
    1  harness/docs/upgrade/evidence/A5-h3-dual-end-review-20260923-03/matrix-coverage-recheck.json
    4  harness/docs/upgrade/evidence/A5-h3-dual-end-review-20260923-03/snapshot-recheck.json
  156  harness/docs/upgrade/evidence/A5-h3-dual-end-review-20260923-03/target-evidence-recheck.json
    3  harness/docs/upgrade/evidence/A5-h3-dual-end-review-20260924-04-pilot-gate/h3-dual-end-review.json
    2  harness/docs/upgrade/evidence/A5-h3-dual-end-review-20260924-04-pilot-gate/source-fingerprint-refreeze.json
   10  harness/docs/upgrade/evidence/A5-harness-preflight-10-input-gate/inputs.json
    8  harness/docs/upgrade/evidence/A5-harness-preflight-11-canonical-consumption/command.json
  119  harness/docs/upgrade/evidence/A5-harness-preflight-11-canonical-consumption/input-stability.json
  119  harness/docs/upgrade/evidence/A5-harness-preflight-11-canonical-consumption/inputs.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-11-canonical-consumption/readiness.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-12-host-sources/manifest.json
   24  harness/docs/upgrade/evidence/A5-harness-preflight-12-host-sources/receipts.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-12-host-sources/tasks/django__django-10914/download-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-12-host-sources/tasks/django__django-10914/source-receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-12-host-sources/tasks/django__django-13265/download-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-12-host-sources/tasks/django__django-13265/source-receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-12-host-sources/tasks/django__django-13448/download-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-12-host-sources/tasks/django__django-13448/source-receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-12-host-sources/tasks/django__django-13590/download-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-12-host-sources/tasks/django__django-13590/source-receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-12-host-sources/tasks/django__django-15781/download-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-12-host-sources/tasks/django__django-15781/source-receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-12-host-sources/tasks/pytest-dev__pytest-5103/download-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-12-host-sources/tasks/pytest-dev__pytest-5103/source-receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-12-host-sources/tasks/pytest-dev__pytest-7220/download-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-12-host-sources/tasks/pytest-dev__pytest-7220/source-receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-12-host-sources/tasks/pytest-dev__pytest-7432/download-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-12-host-sources/tasks/pytest-dev__pytest-7432/source-receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-12-host-sources/tasks/pytest-dev__pytest-8365/download-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-12-host-sources/tasks/pytest-dev__pytest-8365/source-receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-12-host-sources/tasks/pytest-dev__pytest-9359/download-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-12-host-sources/tasks/pytest-dev__pytest-9359/source-receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-12-host-sources/tasks/scikit-learn__scikit-learn-10297/download-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-12-host-sources/tasks/scikit-learn__scikit-learn-10297/source-receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-12-host-sources/tasks/scikit-learn__scikit-learn-25500/download-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-12-host-sources/tasks/scikit-learn__scikit-learn-25500/source-receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-12-host-sources/tasks/scikit-learn__scikit-learn-25570/download-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-12-host-sources/tasks/scikit-learn__scikit-learn-25570/source-receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-12-host-sources/tasks/scikit-learn__scikit-learn-25638/download-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-12-host-sources/tasks/scikit-learn__scikit-learn-25638/source-receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-12-host-sources/tasks/scikit-learn__scikit-learn-25747/download-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-12-host-sources/tasks/scikit-learn__scikit-learn-25747/source-receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-12-host-sources/tasks/sphinx-doc__sphinx-10451/download-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-12-host-sources/tasks/sphinx-doc__sphinx-10451/source-receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-12-host-sources/tasks/sphinx-doc__sphinx-8595/download-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-12-host-sources/tasks/sphinx-doc__sphinx-8595/source-receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-12-host-sources/tasks/sphinx-doc__sphinx-8713/download-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-12-host-sources/tasks/sphinx-doc__sphinx-8713/source-receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-12-host-sources/tasks/sphinx-doc__sphinx-8721/download-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-12-host-sources/tasks/sphinx-doc__sphinx-8721/source-receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-12-host-sources/tasks/sympy__sympy-11400/download-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-12-host-sources/tasks/sympy__sympy-11400/source-receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-12-host-sources/tasks/sympy__sympy-18532/download-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-12-host-sources/tasks/sympy__sympy-18532/source-receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-12-host-sources/tasks/sympy__sympy-20154/download-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-12-host-sources/tasks/sympy__sympy-20154/source-receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-12-host-sources/tasks/sympy__sympy-20442/download-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-12-host-sources/tasks/sympy__sympy-20442/source-receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-12-host-sources/tasks/sympy__sympy-24152/download-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-12-host-sources/tasks/sympy__sympy-24152/source-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-13-host-pytest/dependencies-build.json
   24  harness/docs/upgrade/evidence/A5-harness-preflight-13-host-pytest/failure-retry-ledger.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-13-host-pytest/manifest.json
   53  harness/docs/upgrade/evidence/A5-harness-preflight-13-host-pytest/receipts.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-13-host-pytest/tasks/pytest-dev__pytest-5103/image-build.json
    3  harness/docs/upgrade/evidence/A5-harness-preflight-13-host-pytest/tasks/pytest-dev__pytest-5103/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-13-host-pytest/tasks/pytest-dev__pytest-7220/image-build.json
    3  harness/docs/upgrade/evidence/A5-harness-preflight-13-host-pytest/tasks/pytest-dev__pytest-7220/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-13-host-pytest/tasks/pytest-dev__pytest-7432/image-build.json
    3  harness/docs/upgrade/evidence/A5-harness-preflight-13-host-pytest/tasks/pytest-dev__pytest-7432/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-13-host-pytest/tasks/pytest-dev__pytest-8365/image-build.json
    3  harness/docs/upgrade/evidence/A5-harness-preflight-13-host-pytest/tasks/pytest-dev__pytest-8365/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-13-host-pytest/tasks/pytest-dev__pytest-9359/image-build.json
    3  harness/docs/upgrade/evidence/A5-harness-preflight-13-host-pytest/tasks/pytest-dev__pytest-9359/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-14-host-pytest/dependencies-build.json
   24  harness/docs/upgrade/evidence/A5-harness-preflight-14-host-pytest/failure-retry-ledger.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-14-host-pytest/manifest.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-14-host-pytest/tasks/pytest-dev__pytest-5103/image-build.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-14-host-pytest/tasks/pytest-dev__pytest-7220/image-build.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-14-host-pytest/tasks/pytest-dev__pytest-7432/image-build.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-14-host-pytest/tasks/pytest-dev__pytest-8365/image-build.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-14-host-pytest/tasks/pytest-dev__pytest-9359/image-build.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-15-pytest9359-py39/orchestration-failure.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-16-pytest9359-py39/dependencies-build.json
   24  harness/docs/upgrade/evidence/A5-harness-preflight-16-pytest9359-py39/failure-retry-ledger.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-16-pytest9359-py39/manifest.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-16-pytest9359-py39/tasks/pytest-dev__pytest-9359/image-build.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-17-pytest5103-deps/dependencies-build.json
   24  harness/docs/upgrade/evidence/A5-harness-preflight-17-pytest5103-deps/failure-retry-ledger.json
    3  harness/docs/upgrade/evidence/A5-harness-preflight-17-pytest5103-deps/manifest.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-17-pytest5103-deps/tasks/pytest-dev__pytest-5103/image-build.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-18-pytest5103-plugins/dependencies-build.json
   24  harness/docs/upgrade/evidence/A5-harness-preflight-18-pytest5103-plugins/failure-retry-ledger.json
    3  harness/docs/upgrade/evidence/A5-harness-preflight-18-pytest5103-plugins/manifest.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-18-pytest5103-plugins/tasks/pytest-dev__pytest-5103/image-build.json
   17  harness/docs/upgrade/evidence/A5-harness-preflight-19-final-audit/environment-receipts.json
  128  harness/docs/upgrade/evidence/A5-harness-preflight-19-final-audit/failure-retry-ledger.json
    8  harness/docs/upgrade/evidence/A5-harness-preflight-19-final-audit/input-bindings.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-20-image-backed/handoff.json
   24  harness/docs/upgrade/evidence/A5-harness-preflight-20-image-backed/receipts.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-20-image-backed/tasks/django__django-10914/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-20-image-backed/tasks/django__django-13265/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-20-image-backed/tasks/django__django-13448/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-20-image-backed/tasks/django__django-13590/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-20-image-backed/tasks/django__django-15781/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-20-image-backed/tasks/pytest-dev__pytest-5103/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-20-image-backed/tasks/pytest-dev__pytest-7220/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-20-image-backed/tasks/pytest-dev__pytest-7432/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-20-image-backed/tasks/pytest-dev__pytest-8365/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-20-image-backed/tasks/pytest-dev__pytest-9359/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-20-image-backed/tasks/scikit-learn__scikit-learn-10297/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-20-image-backed/tasks/scikit-learn__scikit-learn-25500/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-20-image-backed/tasks/scikit-learn__scikit-learn-25570/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-20-image-backed/tasks/scikit-learn__scikit-learn-25638/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-20-image-backed/tasks/scikit-learn__scikit-learn-25747/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-20-image-backed/tasks/sphinx-doc__sphinx-10451/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-20-image-backed/tasks/sphinx-doc__sphinx-8595/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-20-image-backed/tasks/sphinx-doc__sphinx-8713/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-20-image-backed/tasks/sphinx-doc__sphinx-8721/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-20-image-backed/tasks/sympy__sympy-11400/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-20-image-backed/tasks/sympy__sympy-18532/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-20-image-backed/tasks/sympy__sympy-20154/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-20-image-backed/tasks/sympy__sympy-20442/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-20-image-backed/tasks/sympy__sympy-24152/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-20b-image-backed/handoff.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-20b-image-backed/receipts.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-20b-image-backed/tasks/pytest-dev__pytest-8365/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-20c-image-backed/handoff.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-20c-image-backed/receipts.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-20c-image-backed/tasks/pytest-dev__pytest-8365/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-21-image-contexts/handoff.json
   48  harness/docs/upgrade/evidence/A5-harness-preflight-21-image-contexts/receipts.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-21-image-contexts/tasks/django__django-10914/receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-21-image-contexts/tasks/django__django-13265/receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-21-image-contexts/tasks/django__django-13448/receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-21-image-contexts/tasks/django__django-13590/receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-21-image-contexts/tasks/django__django-15781/receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-21-image-contexts/tasks/pytest-dev__pytest-5103/receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-21-image-contexts/tasks/pytest-dev__pytest-7220/receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-21-image-contexts/tasks/pytest-dev__pytest-7432/receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-21-image-contexts/tasks/pytest-dev__pytest-8365/receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-21-image-contexts/tasks/pytest-dev__pytest-9359/receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-21-image-contexts/tasks/scikit-learn__scikit-learn-10297/receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-21-image-contexts/tasks/scikit-learn__scikit-learn-25500/receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-21-image-contexts/tasks/scikit-learn__scikit-learn-25570/receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-21-image-contexts/tasks/scikit-learn__scikit-learn-25638/receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-21-image-contexts/tasks/scikit-learn__scikit-learn-25747/receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-21-image-contexts/tasks/sphinx-doc__sphinx-10451/receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-21-image-contexts/tasks/sphinx-doc__sphinx-8595/receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-21-image-contexts/tasks/sphinx-doc__sphinx-8713/receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-21-image-contexts/tasks/sphinx-doc__sphinx-8721/receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-21-image-contexts/tasks/sympy__sympy-11400/receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-21-image-contexts/tasks/sympy__sympy-18532/receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-21-image-contexts/tasks/sympy__sympy-20154/receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-21-image-contexts/tasks/sympy__sympy-20442/receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-21-image-contexts/tasks/sympy__sympy-24152/receipt.json
   24  harness/docs/upgrade/evidence/A5-harness-preflight-22-typed-tree/receipts.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-22-typed-tree/tasks/django__django-10914/typed-tree-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-22-typed-tree/tasks/django__django-13265/typed-tree-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-22-typed-tree/tasks/django__django-13448/typed-tree-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-22-typed-tree/tasks/django__django-13590/typed-tree-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-22-typed-tree/tasks/django__django-15781/typed-tree-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-22-typed-tree/tasks/pytest-dev__pytest-5103/typed-tree-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-22-typed-tree/tasks/pytest-dev__pytest-7220/typed-tree-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-22-typed-tree/tasks/pytest-dev__pytest-7432/typed-tree-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-22-typed-tree/tasks/pytest-dev__pytest-8365/typed-tree-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-22-typed-tree/tasks/pytest-dev__pytest-9359/typed-tree-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-22-typed-tree/tasks/scikit-learn__scikit-learn-10297/typed-tree-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-22-typed-tree/tasks/scikit-learn__scikit-learn-25500/typed-tree-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-22-typed-tree/tasks/scikit-learn__scikit-learn-25570/typed-tree-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-22-typed-tree/tasks/scikit-learn__scikit-learn-25638/typed-tree-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-22-typed-tree/tasks/scikit-learn__scikit-learn-25747/typed-tree-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-22-typed-tree/tasks/sphinx-doc__sphinx-10451/typed-tree-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-22-typed-tree/tasks/sphinx-doc__sphinx-8595/typed-tree-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-22-typed-tree/tasks/sphinx-doc__sphinx-8713/typed-tree-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-22-typed-tree/tasks/sphinx-doc__sphinx-8721/typed-tree-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-22-typed-tree/tasks/sympy__sympy-11400/typed-tree-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-22-typed-tree/tasks/sympy__sympy-18532/typed-tree-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-22-typed-tree/tasks/sympy__sympy-20154/typed-tree-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-22-typed-tree/tasks/sympy__sympy-20442/typed-tree-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-22-typed-tree/tasks/sympy__sympy-24152/typed-tree-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-23-transport-smoke/audit.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-23-transport-smoke/tasks/django__django-10914/build-log.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-23-transport-smoke/tasks/django__django-13265/build-log.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-23-transport-smoke/tasks/django__django-13448/build-log.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-23-transport-smoke/tasks/django__django-13590/build-log.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-23-transport-smoke/tasks/django__django-15781/build-log.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-23-transport-smoke/tasks/pytest-dev__pytest-5103/build-log.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-23-transport-smoke/tasks/pytest-dev__pytest-7220/build-log.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-23-transport-smoke/tasks/pytest-dev__pytest-7432/build-log.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-23-transport-smoke/tasks/pytest-dev__pytest-8365/build-log.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-23-transport-smoke/tasks/pytest-dev__pytest-9359/build-log.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-23-transport-smoke/tasks/scikit-learn__scikit-learn-10297/build-log.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-23-transport-smoke/tasks/scikit-learn__scikit-learn-25500/build-log.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-23-transport-smoke/tasks/scikit-learn__scikit-learn-25570/build-log.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-23-transport-smoke/tasks/scikit-learn__scikit-learn-25638/build-log.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-23-transport-smoke/tasks/scikit-learn__scikit-learn-25747/build-log.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-23-transport-smoke/tasks/sphinx-doc__sphinx-10451/build-log.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-23-transport-smoke/tasks/sphinx-doc__sphinx-8595/build-log.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-23-transport-smoke/tasks/sphinx-doc__sphinx-8713/build-log.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-23-transport-smoke/tasks/sphinx-doc__sphinx-8721/build-log.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-23-transport-smoke/tasks/sympy__sympy-11400/build-log.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-23-transport-smoke/tasks/sympy__sympy-18532/build-log.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-23-transport-smoke/tasks/sympy__sympy-20154/build-log.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-23-transport-smoke/tasks/sympy__sympy-20442/build-log.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-23-transport-smoke/tasks/sympy__sympy-24152/build-log.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-25-repo-baseline-sympy20154/receipts.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-25-repo-baseline-sympy20154/tasks/sympy__sympy-20154/receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-25b-repo-baseline-sympy20154/receipts.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-25b-repo-baseline-sympy20154/tasks/sympy__sympy-20154/receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-25c-repo-baseline-sympy20154/receipts.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-25c-repo-baseline-sympy20154/tasks/sympy__sympy-20154/receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-25d-repo-baseline-sympy20154/receipts.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-25d-repo-baseline-sympy20154/tasks/sympy__sympy-20154/receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-25e-repo-baseline-sympy20154/receipts.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-25e-repo-baseline-sympy20154/tasks/sympy__sympy-20154/receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-25f-repo-baseline-sympy20154/receipts.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-25f-repo-baseline-sympy20154/tasks/sympy__sympy-20154/receipt.json
    6  harness/docs/upgrade/evidence/A5-harness-preflight-25g-repo-baseline-sympy20154/receipts.json
    6  harness/docs/upgrade/evidence/A5-harness-preflight-25g-repo-baseline-sympy20154/tasks/sympy__sympy-20154/receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-25h-repo-baseline-sympy20154/receipts.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-25h-repo-baseline-sympy20154/tasks/sympy__sympy-20154/receipt.json
    6  harness/docs/upgrade/evidence/A5-harness-preflight-25k-repo-baseline-sphinx8595/receipts.json
    6  harness/docs/upgrade/evidence/A5-harness-preflight-25k-repo-baseline-sphinx8595/tasks/sphinx-doc__sphinx-8595/receipt.json
    6  harness/docs/upgrade/evidence/A5-harness-preflight-25l-repo-baseline-sphinx8595/receipts.json
    6  harness/docs/upgrade/evidence/A5-harness-preflight-25l-repo-baseline-sphinx8595/tasks/sphinx-doc__sphinx-8595/receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-27-repo-baseline/tasks/pytest-dev__pytest-7432/receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-27-repo-baseline/tasks/scikit-learn__scikit-learn-10297/receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-27-repo-baseline/tasks/scikit-learn__scikit-learn-25500/receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-27-repo-baseline/tasks/scikit-learn__scikit-learn-25570/receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-27-repo-baseline/tasks/scikit-learn__scikit-learn-25638/receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-27-repo-baseline/tasks/scikit-learn__scikit-learn-25747/receipt.json
    6  harness/docs/upgrade/evidence/A5-harness-preflight-27-repo-baseline/tasks/sphinx-doc__sphinx-10451/receipt.json
    6  harness/docs/upgrade/evidence/A5-harness-preflight-27-repo-baseline/tasks/sphinx-doc__sphinx-8595/receipt.json
    6  harness/docs/upgrade/evidence/A5-harness-preflight-27-repo-baseline/tasks/sphinx-doc__sphinx-8713/receipt.json
    6  harness/docs/upgrade/evidence/A5-harness-preflight-27-repo-baseline/tasks/sphinx-doc__sphinx-8721/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-28-django13265-module/input-binding.json
   10  harness/docs/upgrade/evidence/A5-harness-preflight-33-sklearn-compiler/receipts.json
    5  harness/docs/upgrade/evidence/A5-harness-preflight-33-sklearn-compiler/tasks/scikit-learn__scikit-learn-25500/receipt.json
    5  harness/docs/upgrade/evidence/A5-harness-preflight-33-sklearn-compiler/tasks/scikit-learn__scikit-learn-25747/receipt.json
   20  harness/docs/upgrade/evidence/A5-harness-preflight-34-sklearn-https/receipts.json
    5  harness/docs/upgrade/evidence/A5-harness-preflight-34-sklearn-https/tasks/scikit-learn__scikit-learn-25500/receipt.json
    5  harness/docs/upgrade/evidence/A5-harness-preflight-34-sklearn-https/tasks/scikit-learn__scikit-learn-25570/receipt.json
    5  harness/docs/upgrade/evidence/A5-harness-preflight-34-sklearn-https/tasks/scikit-learn__scikit-learn-25638/receipt.json
    5  harness/docs/upgrade/evidence/A5-harness-preflight-34-sklearn-https/tasks/scikit-learn__scikit-learn-25747/receipt.json
    8  harness/docs/upgrade/evidence/A5-harness-preflight-35-sphinx-test-files/tasks/sphinx-doc__sphinx-10451/receipt.json
    8  harness/docs/upgrade/evidence/A5-harness-preflight-35-sphinx-test-files/tasks/sphinx-doc__sphinx-8595/receipt.json
    8  harness/docs/upgrade/evidence/A5-harness-preflight-35-sphinx-test-files/tasks/sphinx-doc__sphinx-8713/receipt.json
    8  harness/docs/upgrade/evidence/A5-harness-preflight-35-sphinx-test-files/tasks/sphinx-doc__sphinx-8721/receipt.json
    8  harness/docs/upgrade/evidence/A5-harness-preflight-36-repo-compat/tasks/sphinx-doc__sphinx-8721/receipt.json
    6  harness/docs/upgrade/evidence/A5-harness-preflight-38-sklearn-snapshot-smoke/receipts.json
    6  harness/docs/upgrade/evidence/A5-harness-preflight-38-sklearn-snapshot-smoke/tasks/scikit-learn__scikit-learn-25747/receipt.json
   24  harness/docs/upgrade/evidence/A5-harness-preflight-40-sklearn-full/receipts.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-40-sklearn-full/tasks/scikit-learn__scikit-learn-10297/baseline-image-build.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-40-sklearn-full/tasks/scikit-learn__scikit-learn-10297/known-good-image-build.json
    6  harness/docs/upgrade/evidence/A5-harness-preflight-40-sklearn-full/tasks/scikit-learn__scikit-learn-10297/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-40-sklearn-full/tasks/scikit-learn__scikit-learn-25500/baseline-image-build.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-40-sklearn-full/tasks/scikit-learn__scikit-learn-25500/known-good-image-build.json
    6  harness/docs/upgrade/evidence/A5-harness-preflight-40-sklearn-full/tasks/scikit-learn__scikit-learn-25500/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-40-sklearn-full/tasks/scikit-learn__scikit-learn-25570/baseline-image-build.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-40-sklearn-full/tasks/scikit-learn__scikit-learn-25570/known-good-image-build.json
    6  harness/docs/upgrade/evidence/A5-harness-preflight-40-sklearn-full/tasks/scikit-learn__scikit-learn-25570/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-40-sklearn-full/tasks/scikit-learn__scikit-learn-25638/baseline-image-build.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-40-sklearn-full/tasks/scikit-learn__scikit-learn-25638/known-good-image-build.json
    6  harness/docs/upgrade/evidence/A5-harness-preflight-40-sklearn-full/tasks/scikit-learn__scikit-learn-25638/receipt.json
  144  harness/docs/upgrade/evidence/A5-harness-preflight-47-final-audit/artifact-bindings.json
  132  harness/docs/upgrade/evidence/A5-harness-preflight-47-final-audit/receipts.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-49-shared-gates/readiness.json
    6  harness/docs/upgrade/evidence/A5-harness-preflight-49-shared-gates/shared-gates.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-50-shared-gates/readiness.json
    6  harness/docs/upgrade/evidence/A5-harness-preflight-50-shared-gates/shared-gates.json
   16  harness/docs/upgrade/evidence/A5-harness-preflight-53-remaining16-sources/receipts.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-53-remaining16-sources/tasks/django__django-10924/download-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-53-remaining16-sources/tasks/django__django-10924/source-receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-53-remaining16-sources/tasks/django__django-11001/download-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-53-remaining16-sources/tasks/django__django-11001/source-receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-53-remaining16-sources/tasks/django__django-11019/download-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-53-remaining16-sources/tasks/django__django-11019/source-receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-53-remaining16-sources/tasks/django__django-11039/download-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-53-remaining16-sources/tasks/django__django-11039/source-receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-53-remaining16-sources/tasks/pytest-dev__pytest-5221/download-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-53-remaining16-sources/tasks/pytest-dev__pytest-5221/source-receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-53-remaining16-sources/tasks/pytest-dev__pytest-5227/download-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-53-remaining16-sources/tasks/pytest-dev__pytest-5227/source-receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-53-remaining16-sources/tasks/pytest-dev__pytest-5413/download-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-53-remaining16-sources/tasks/pytest-dev__pytest-5413/source-receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-53-remaining16-sources/tasks/pytest-dev__pytest-5495/download-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-53-remaining16-sources/tasks/pytest-dev__pytest-5495/source-receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-53-remaining16-sources/tasks/scikit-learn__scikit-learn-10508/download-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-53-remaining16-sources/tasks/scikit-learn__scikit-learn-10508/source-receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-53-remaining16-sources/tasks/scikit-learn__scikit-learn-10949/download-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-53-remaining16-sources/tasks/scikit-learn__scikit-learn-10949/source-receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-53-remaining16-sources/tasks/scikit-learn__scikit-learn-11040/download-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-53-remaining16-sources/tasks/scikit-learn__scikit-learn-11040/source-receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-53-remaining16-sources/tasks/scikit-learn__scikit-learn-11281/download-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-53-remaining16-sources/tasks/scikit-learn__scikit-learn-11281/source-receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-53-remaining16-sources/tasks/sympy__sympy-11870/download-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-53-remaining16-sources/tasks/sympy__sympy-11870/source-receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-53-remaining16-sources/tasks/sympy__sympy-11897/download-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-53-remaining16-sources/tasks/sympy__sympy-11897/source-receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-53-remaining16-sources/tasks/sympy__sympy-12171/download-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-53-remaining16-sources/tasks/sympy__sympy-12171/source-receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-53-remaining16-sources/tasks/sympy__sympy-12236/download-receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-53-remaining16-sources/tasks/sympy__sympy-12236/source-receipt.json
    8  harness/docs/upgrade/evidence/A5-harness-preflight-54-remaining16-pytest/receipts.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-54-remaining16-pytest/tasks/pytest-dev__pytest-5221/receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-54-remaining16-pytest/tasks/pytest-dev__pytest-5227/receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-54-remaining16-pytest/tasks/pytest-dev__pytest-5413/receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-54-remaining16-pytest/tasks/pytest-dev__pytest-5495/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-55-remaining16-transport/tasks/django__django-10924/build-log.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-55-remaining16-transport/tasks/django__django-11001/build-log.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-55-remaining16-transport/tasks/django__django-11019/build-log.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-55-remaining16-transport/tasks/django__django-11039/build-log.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-55-remaining16-transport/tasks/pytest-dev__pytest-5221/build-log.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-55-remaining16-transport/tasks/pytest-dev__pytest-5227/build-log.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-55-remaining16-transport/tasks/pytest-dev__pytest-5413/build-log.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-55-remaining16-transport/tasks/pytest-dev__pytest-5495/build-log.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-55-remaining16-transport/tasks/scikit-learn__scikit-learn-10508/build-log.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-55-remaining16-transport/tasks/scikit-learn__scikit-learn-10949/build-log.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-55-remaining16-transport/tasks/scikit-learn__scikit-learn-11040/build-log.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-55-remaining16-transport/tasks/scikit-learn__scikit-learn-11281/build-log.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-55-remaining16-transport/tasks/sympy__sympy-11870/build-log.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-55-remaining16-transport/tasks/sympy__sympy-11897/build-log.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-55-remaining16-transport/tasks/sympy__sympy-12171/build-log.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-55-remaining16-transport/tasks/sympy__sympy-12236/build-log.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-57-remaining16-baseline/tasks/django__django-10924/baseline-image-build.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-57-remaining16-baseline/tasks/django__django-10924/known-good-image-build.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-57-remaining16-baseline/tasks/django__django-11001/baseline-image-build.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-57-remaining16-baseline/tasks/django__django-11001/known-good-image-build.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-57-remaining16-baseline/tasks/django__django-11019/baseline-image-build.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-57-remaining16-baseline/tasks/django__django-11019/known-good-image-build.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-57-remaining16-baseline/tasks/django__django-11039/baseline-image-build.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-57-remaining16-baseline/tasks/django__django-11039/known-good-image-build.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-57-remaining16-baseline/tasks/pytest-dev__pytest-5221/baseline-image-build.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-57-remaining16-baseline/tasks/pytest-dev__pytest-5221/known-good-image-build.json
    6  harness/docs/upgrade/evidence/A5-harness-preflight-57-remaining16-baseline/tasks/pytest-dev__pytest-5221/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-57-remaining16-baseline/tasks/pytest-dev__pytest-5227/baseline-image-build.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-57-remaining16-baseline/tasks/pytest-dev__pytest-5227/known-good-image-build.json
    6  harness/docs/upgrade/evidence/A5-harness-preflight-57-remaining16-baseline/tasks/pytest-dev__pytest-5227/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-57-remaining16-baseline/tasks/pytest-dev__pytest-5413/baseline-image-build.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-57-remaining16-baseline/tasks/pytest-dev__pytest-5413/known-good-image-build.json
    6  harness/docs/upgrade/evidence/A5-harness-preflight-57-remaining16-baseline/tasks/pytest-dev__pytest-5413/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-57-remaining16-baseline/tasks/pytest-dev__pytest-5495/baseline-image-build.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-57-remaining16-baseline/tasks/pytest-dev__pytest-5495/known-good-image-build.json
    6  harness/docs/upgrade/evidence/A5-harness-preflight-57-remaining16-baseline/tasks/pytest-dev__pytest-5495/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-57-remaining16-baseline/tasks/scikit-learn__scikit-learn-10508/baseline-image-build.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-57-remaining16-baseline/tasks/scikit-learn__scikit-learn-10508/known-good-image-build.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-57-remaining16-baseline/tasks/scikit-learn__scikit-learn-10949/baseline-image-build.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-57-remaining16-baseline/tasks/scikit-learn__scikit-learn-10949/known-good-image-build.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-57-remaining16-baseline/tasks/scikit-learn__scikit-learn-11040/baseline-image-build.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-57-remaining16-baseline/tasks/scikit-learn__scikit-learn-11040/known-good-image-build.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-57-remaining16-baseline/tasks/scikit-learn__scikit-learn-11281/baseline-image-build.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-57-remaining16-baseline/tasks/scikit-learn__scikit-learn-11281/known-good-image-build.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-57-remaining16-baseline/tasks/sympy__sympy-11870/baseline-image-build.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-57-remaining16-baseline/tasks/sympy__sympy-11870/known-good-image-build.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-57-remaining16-baseline/tasks/sympy__sympy-11897/baseline-image-build.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-57-remaining16-baseline/tasks/sympy__sympy-11897/known-good-image-build.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-57-remaining16-baseline/tasks/sympy__sympy-12171/baseline-image-build.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-57-remaining16-baseline/tasks/sympy__sympy-12171/known-good-image-build.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-57-remaining16-baseline/tasks/sympy__sympy-12236/baseline-image-build.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-57-remaining16-baseline/tasks/sympy__sympy-12236/known-good-image-build.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-58-memory-pool-audit/manifest.json
   52  harness/docs/upgrade/evidence/A5-harness-preflight-58-memory-pool-audit/receipts.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-59-shared-gates/readiness.json
    6  harness/docs/upgrade/evidence/A5-harness-preflight-59-shared-gates/shared-gates.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-60-shared-gates/readiness.json
    7  harness/docs/upgrade/evidence/A5-harness-preflight-60-shared-gates/shared-gates.json
    8  harness/docs/upgrade/evidence/A5-harness-preflight-61-history-baseline/receipts.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-61-history-baseline/tasks/django__django-10914/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-61-history-baseline/tasks/pytest-dev__pytest-5103/baseline-image-build.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-61-history-baseline/tasks/pytest-dev__pytest-5103/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-61-history-baseline/tasks/scikit-learn__scikit-learn-10297/baseline-image-build.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-61-history-baseline/tasks/scikit-learn__scikit-learn-10297/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-61-history-baseline/tasks/sympy__sympy-11400/baseline-image-build.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-61-history-baseline/tasks/sympy__sympy-11400/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-62-history-baseline-retry/tasks/django__django-10914/baseline-image-build.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-62-history-baseline-retry/tasks/django__django-10914/known-good-image-build.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-62-history-baseline-retry/tasks/pytest-dev__pytest-5103/baseline-image-build.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-62-history-baseline-retry/tasks/pytest-dev__pytest-5103/known-good-image-build.json
    6  harness/docs/upgrade/evidence/A5-harness-preflight-62-history-baseline-retry/tasks/pytest-dev__pytest-5103/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-62-history-baseline-retry/tasks/scikit-learn__scikit-learn-10297/baseline-image-build.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-62-history-baseline-retry/tasks/scikit-learn__scikit-learn-10297/known-good-image-build.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-62-history-baseline-retry/tasks/sympy__sympy-11400/baseline-image-build.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-62-history-baseline-retry/tasks/sympy__sympy-11400/known-good-image-build.json
    8  harness/docs/upgrade/evidence/A5-harness-preflight-62-history-baseline/receipts.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-62-history-baseline/tasks/django__django-10914/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-62-history-baseline/tasks/pytest-dev__pytest-5103/baseline-image-build.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-62-history-baseline/tasks/pytest-dev__pytest-5103/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-62-history-baseline/tasks/scikit-learn__scikit-learn-10297/baseline-image-build.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-62-history-baseline/tasks/scikit-learn__scikit-learn-10297/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-62-history-baseline/tasks/sympy__sympy-11400/baseline-image-build.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-62-history-baseline/tasks/sympy__sympy-11400/receipt.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-63-grader-calibration/receipts.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-63-grader-calibration/tasks/pytest-dev__pytest-5221/calibration.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-63-grader-calibration/tasks/pytest-dev__pytest-5227/calibration.json
    2  harness/docs/upgrade/evidence/A5-harness-preflight-64-grader-calibration/receipts.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-64-grader-calibration/tasks/pytest-dev__pytest-5221/calibration.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-64-grader-calibration/tasks/pytest-dev__pytest-5227/calibration.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-65-grader-calibration/tasks/django__django-10924/calibration.json
   11  harness/docs/upgrade/evidence/A5-harness-preflight-66-grader-calibration/receipts.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-66-grader-calibration/tasks/django__django-10924/calibration.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-66-grader-calibration/tasks/django__django-11039/calibration.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-66-grader-calibration/tasks/pytest-dev__pytest-5221/calibration.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-66-grader-calibration/tasks/pytest-dev__pytest-5227/calibration.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-66-grader-calibration/tasks/scikit-learn__scikit-learn-10508/calibration.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-66-grader-calibration/tasks/scikit-learn__scikit-learn-10949/calibration.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-66-grader-calibration/tasks/scikit-learn__scikit-learn-11040/calibration.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-66-grader-calibration/tasks/scikit-learn__scikit-learn-11281/calibration.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-66-grader-calibration/tasks/sympy__sympy-11870/calibration.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-66-grader-calibration/tasks/sympy__sympy-11897/calibration.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-66-grader-calibration/tasks/sympy__sympy-12171/calibration.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-67-grader-calibration-retry/receipts.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-67-grader-calibration-retry/tasks/pytest-dev__pytest-5227/calibration.json
    3  harness/docs/upgrade/evidence/A5-harness-preflight-68-memory-gates-final/manifest.json
   67  harness/docs/upgrade/evidence/A5-harness-preflight-68-memory-gates-final/receipts.json
    3  harness/docs/upgrade/evidence/A5-harness-preflight-69-memory-gates-final/manifest.json
   63  harness/docs/upgrade/evidence/A5-harness-preflight-69-memory-gates-final/receipts.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-70-shared-gates/readiness.json
    7  harness/docs/upgrade/evidence/A5-harness-preflight-70-shared-gates/shared-gates.json
    3  harness/docs/upgrade/evidence/A5-harness-preflight-71-memory-gates-final/manifest.json
   63  harness/docs/upgrade/evidence/A5-harness-preflight-71-memory-gates-final/receipts.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-72-shared-gates/readiness.json
    7  harness/docs/upgrade/evidence/A5-harness-preflight-72-shared-gates/shared-gates.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-74-s1-smoke/django__django-10914-r2/min-gate.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-74-s1-smoke/django__django-10914-r2/public-input.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-74-s1-smoke/django__django-10914-reverify/min-gate.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-74-s1-smoke/django__django-10914-reverify/public-input.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-74-s1-smoke/django__django-10914/min-gate.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-74-s1-smoke/django__django-10914/public-input.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-74-s1-smoke/django__django-10924-reverify/min-gate.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-74-s1-smoke/django__django-10924-reverify/public-input.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-74-s1-smoke/django__django-10924/min-gate.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-74-s1-smoke/django__django-10924/public-input.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-74-s1-smoke/pytest-dev__pytest-5103-reverify/min-gate.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-74-s1-smoke/pytest-dev__pytest-5103-reverify/public-input.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-74-s1-smoke/pytest-dev__pytest-5103/min-gate.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-74-s1-smoke/pytest-dev__pytest-5103/public-input.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-74-s1-smoke/scikit-learn__scikit-learn-10297-reverify/min-gate.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-74-s1-smoke/scikit-learn__scikit-learn-10297-reverify/public-input.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-74-s1-smoke/scikit-learn__scikit-learn-10297/min-gate.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-74-s1-smoke/scikit-learn__scikit-learn-10297/public-input.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-74-s1-smoke/sympy__sympy-11400-reverify/min-gate.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-74-s1-smoke/sympy__sympy-11400-reverify/public-input.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-74-s1-smoke/sympy__sympy-11400/min-gate.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-74-s1-smoke/sympy__sympy-11400/public-input.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-74-s1-smoke/sympy__sympy-11870-reverify/min-gate.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-74-s1-smoke/sympy__sympy-11870-reverify/public-input.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-74-s1-smoke/sympy__sympy-11870/min-gate.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-74-s1-smoke/sympy__sympy-11870/public-input.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-75-s1-smoke/django__django-10914-reverify/min-gate.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-75-s1-smoke/django__django-10914-reverify/public-input.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-75-s1-smoke/django__django-10914/min-gate.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-75-s1-smoke/django__django-10914/public-input.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-75-s1-smoke/django__django-10924-reverify/min-gate.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-75-s1-smoke/django__django-10924-reverify/public-input.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-75-s1-smoke/django__django-10924/min-gate.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-75-s1-smoke/django__django-10924/public-input.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-75-s1-smoke/pytest-dev__pytest-5103-reverify/min-gate.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-75-s1-smoke/pytest-dev__pytest-5103-reverify/public-input.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-75-s1-smoke/pytest-dev__pytest-5103/min-gate.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-75-s1-smoke/pytest-dev__pytest-5103/public-input.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-75-s1-smoke/scikit-learn__scikit-learn-10297-reverify/min-gate.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-75-s1-smoke/scikit-learn__scikit-learn-10297-reverify/public-input.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-75-s1-smoke/scikit-learn__scikit-learn-10297/min-gate.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-75-s1-smoke/scikit-learn__scikit-learn-10297/public-input.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-75-s1-smoke/sympy__sympy-11400-reverify/min-gate.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-75-s1-smoke/sympy__sympy-11400-reverify/public-input.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-75-s1-smoke/sympy__sympy-11400/min-gate.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-75-s1-smoke/sympy__sympy-11400/public-input.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-75-s1-smoke/sympy__sympy-11870-reverify/min-gate.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-75-s1-smoke/sympy__sympy-11870-reverify/public-input.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-75-s1-smoke/sympy__sympy-11870/min-gate.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-75-s1-smoke/sympy__sympy-11870/public-input.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-76-s2/builds/django__django-11039/min-gate.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-76-s2/builds/django__django-11039/public-input.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-76-s2/builds/pytest-dev__pytest-5221/min-gate.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-76-s2/builds/pytest-dev__pytest-5221/public-input.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-76-s2/builds/pytest-dev__pytest-5227-reverify/min-gate.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-76-s2/builds/pytest-dev__pytest-5227-reverify/public-input.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-76-s2/builds/pytest-dev__pytest-5227/min-gate.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-76-s2/builds/pytest-dev__pytest-5227/public-input.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-76-s2/builds/scikit-learn__scikit-learn-10508/min-gate.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-76-s2/builds/scikit-learn__scikit-learn-10508/public-input.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-76-s2/builds/scikit-learn__scikit-learn-10949/min-gate.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-76-s2/builds/scikit-learn__scikit-learn-10949/public-input.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-76-s2/builds/scikit-learn__scikit-learn-11040/min-gate.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-76-s2/builds/scikit-learn__scikit-learn-11040/public-input.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-76-s2/builds/scikit-learn__scikit-learn-11281/min-gate.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-76-s2/builds/scikit-learn__scikit-learn-11281/public-input.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-76-s2/builds/sympy__sympy-11897/min-gate.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-76-s2/builds/sympy__sympy-11897/public-input.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-76-s2/builds/sympy__sympy-12171/min-gate.json
    2  harness/docs/upgrade/evidence/A5-memory-pool-76-s2/builds/sympy__sympy-12171/public-input.json
    1  harness/docs/upgrade/evidence/A5-memory-pool-76-s2/provenance-review-carry-forward/reviews/django__django-10914.json
    1  harness/docs/upgrade/evidence/A5-memory-pool-76-s2/provenance-review-carry-forward/reviews/django__django-10924.json
    1  harness/docs/upgrade/evidence/A5-memory-pool-76-s2/provenance-review-carry-forward/reviews/pytest-dev__pytest-5103.json
    1  harness/docs/upgrade/evidence/A5-memory-pool-76-s2/provenance-review-carry-forward/reviews/scikit-learn__scikit-learn-10297.json
    1  harness/docs/upgrade/evidence/A5-memory-pool-76-s2/provenance-review-carry-forward/reviews/sympy__sympy-11400.json
    1  harness/docs/upgrade/evidence/A5-memory-pool-76-s2/provenance-review-expand/reviews/django__django-11039.json
    1  harness/docs/upgrade/evidence/A5-memory-pool-76-s2/provenance-review-expand/reviews/pytest-dev__pytest-5221.json
    1  harness/docs/upgrade/evidence/A5-memory-pool-76-s2/provenance-review-expand/reviews/scikit-learn__scikit-learn-10949.json
    1  harness/docs/upgrade/evidence/A5-memory-pool-76-s2/provenance-review-expand/reviews/scikit-learn__scikit-learn-11040.json
    1  harness/docs/upgrade/evidence/A5-memory-pool-76-s2/provenance-review-expand/reviews/scikit-learn__scikit-learn-11281.json
    1  harness/docs/upgrade/evidence/A5-memory-pool-76-s2/provenance-review-expand/reviews/sympy__sympy-12171.json
  117  harness/docs/upgrade/evidence/A5-pilot-grader-input-20260923-02.json
  123  harness/docs/upgrade/evidence/A5-pilot-grader-input-20260923-03.json
   16  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-01/receipts.json
    1  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-01/tasks/django__django-13448/calibration.json
    1  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-01/tasks/django__django-13590/calibration.json
    1  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-01/tasks/django__django-15781/calibration.json
    1  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-01/tasks/pytest-dev__pytest-7432/calibration.json
    1  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-01/tasks/scikit-learn__scikit-learn-25500/calibration.json
    1  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-01/tasks/scikit-learn__scikit-learn-25570/calibration.json
    1  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-01/tasks/scikit-learn__scikit-learn-25638/calibration.json
    1  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-01/tasks/scikit-learn__scikit-learn-25747/calibration.json
    1  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-01/tasks/sphinx-doc__sphinx-10451/calibration.json
    1  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-01/tasks/sphinx-doc__sphinx-8595/calibration.json
    1  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-01/tasks/sphinx-doc__sphinx-8713/calibration.json
    1  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-01/tasks/sphinx-doc__sphinx-8721/calibration.json
    1  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-01/tasks/sympy__sympy-18532/calibration.json
    1  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-01/tasks/sympy__sympy-20154/calibration.json
    1  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-01/tasks/sympy__sympy-20442/calibration.json
    1  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-01/tasks/sympy__sympy-24152/calibration.json
    3  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-02/manifest.json
   38  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-02/receipts.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-02/tasks/django__django-13448/calibration.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-02/tasks/django__django-13590/calibration.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-02/tasks/django__django-15781/calibration.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-02/tasks/pytest-dev__pytest-7220/calibration.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-02/tasks/pytest-dev__pytest-7432/calibration.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-02/tasks/pytest-dev__pytest-8365/calibration.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-02/tasks/pytest-dev__pytest-9359/calibration.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-02/tasks/scikit-learn__scikit-learn-25500/calibration.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-02/tasks/scikit-learn__scikit-learn-25570/calibration.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-02/tasks/scikit-learn__scikit-learn-25638/calibration.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-02/tasks/scikit-learn__scikit-learn-25747/calibration.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-02/tasks/sphinx-doc__sphinx-10451/calibration.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-02/tasks/sphinx-doc__sphinx-8595/calibration.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-02/tasks/sphinx-doc__sphinx-8713/calibration.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-02/tasks/sphinx-doc__sphinx-8721/calibration.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-02/tasks/sympy__sympy-18532/calibration.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-02/tasks/sympy__sympy-20154/calibration.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-02/tasks/sympy__sympy-20442/calibration.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-02/tasks/sympy__sympy-24152/calibration.json
    3  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-03/manifest.json
   11  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-03/receipts.json
    3  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-03/tasks/pytest-dev__pytest-7220/calibration.json
    3  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-03/tasks/pytest-dev__pytest-8365/calibration.json
    3  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-03/tasks/pytest-dev__pytest-9359/calibration.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-03/tasks/sympy__sympy-18532/calibration.json
    3  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-04/manifest.json
   12  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-04/receipts.json
    4  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-04/tasks/pytest-dev__pytest-7220/calibration.json
    4  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-04/tasks/pytest-dev__pytest-8365/calibration.json
    4  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-04/tasks/pytest-dev__pytest-9359/calibration.json
    3  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-05/manifest.json
   12  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-05/receipts.json
    4  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-05/tasks/pytest-dev__pytest-7220/calibration.json
    4  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-05/tasks/pytest-dev__pytest-8365/calibration.json
    4  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-05/tasks/pytest-dev__pytest-9359/calibration.json
   25  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-06/manifest.json
   44  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-06/receipts.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-06/tasks/django__django-13448/calibration.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-06/tasks/django__django-13590/calibration.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-06/tasks/django__django-15781/calibration.json
    4  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-06/tasks/pytest-dev__pytest-7220/calibration.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-06/tasks/pytest-dev__pytest-7432/calibration.json
    4  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-06/tasks/pytest-dev__pytest-8365/calibration.json
    4  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-06/tasks/pytest-dev__pytest-9359/calibration.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-06/tasks/scikit-learn__scikit-learn-25500/calibration.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-06/tasks/scikit-learn__scikit-learn-25570/calibration.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-06/tasks/scikit-learn__scikit-learn-25638/calibration.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-06/tasks/scikit-learn__scikit-learn-25747/calibration.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-06/tasks/sphinx-doc__sphinx-10451/calibration.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-06/tasks/sphinx-doc__sphinx-8595/calibration.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-06/tasks/sphinx-doc__sphinx-8713/calibration.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-06/tasks/sphinx-doc__sphinx-8721/calibration.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-06/tasks/sympy__sympy-18532/calibration.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-06/tasks/sympy__sympy-20154/calibration.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-06/tasks/sympy__sympy-20442/calibration.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-06/tasks/sympy__sympy-24152/calibration.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-07/django-contract-audit.json
   25  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-07/manifest.json
   44  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-07/receipts.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-07/tasks/django__django-13448/calibration.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-07/tasks/django__django-13590/calibration.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-07/tasks/django__django-15781/calibration.json
    4  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-07/tasks/pytest-dev__pytest-7220/calibration.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-07/tasks/pytest-dev__pytest-7432/calibration.json
    4  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-07/tasks/pytest-dev__pytest-8365/calibration.json
    4  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-07/tasks/pytest-dev__pytest-9359/calibration.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-07/tasks/scikit-learn__scikit-learn-25500/calibration.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-07/tasks/scikit-learn__scikit-learn-25570/calibration.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-07/tasks/scikit-learn__scikit-learn-25638/calibration.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-07/tasks/scikit-learn__scikit-learn-25747/calibration.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-07/tasks/sphinx-doc__sphinx-10451/calibration.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-07/tasks/sphinx-doc__sphinx-8595/calibration.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-07/tasks/sphinx-doc__sphinx-8713/calibration.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-07/tasks/sphinx-doc__sphinx-8721/calibration.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-07/tasks/sympy__sympy-18532/calibration.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-07/tasks/sympy__sympy-20154/calibration.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-07/tasks/sympy__sympy-20442/calibration.json
    2  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-07/tasks/sympy__sympy-24152/calibration.json
   79  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-08-planA/h3-input-package.json
    1  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-08-planA/pending.json
   60  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-08-planA/pilot20-grader-ledger.json
    5  harness/docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-08-planA/plan-a-disposition.json
   28  harness/docs/upgrade/evidence/A5-real240-77-harness-preflight/failure-ledger-ref.json
   12  harness/docs/upgrade/evidence/A5-real240-77-harness-preflight/memory-snapshot-manifest.json
   13  harness/docs/upgrade/evidence/A5-real240-77-harness-preflight/readiness.json
    9  harness/docs/upgrade/evidence/A5-real240-78-pilot-lock/readiness.json
    4  harness/docs/upgrade/evidence/A5-real240-79-fixture-wiring/fixture-ledger.json
    2  harness/docs/upgrade/evidence/H3/README.md
    2  harness/docs/upgrade/evidence/H4/README.md
    4  harness/docs/upgrade/evidence/HP-01/REPORT.md
    5  harness/docs/upgrade/evidence/HP-02/REPORT.md
    1  harness/docs/upgrade/evidence/HP-03/CODEX-ACCEPTANCE-20260919.md
    3  harness/docs/upgrade/evidence/HP-04/REPORT.md
    2  harness/docs/upgrade/evidence/full-repo-grader/audit-01/audit.json
    2  harness/docs/upgrade/evidence/full-repo-grader/audit-01/public-handoff.json
    1  harness/docs/upgrade/evidence/full-repo-grader/validation-01/manifest.json
    1  harness/docs/upgrade/evidence/full-repo-grader/validation-02/manifest.json
    1  harness/docs/upgrade/evidence/full-repo-grader/validation-03/manifest.json
    1  harness/docs/upgrade/evidence/full-repo-grader/validation-04/manifest.json
    1  harness/scripts/audit/README.md
    1  harness/scripts/audit/audit_b0_deltas.py
    1  harness/scripts/audit/audit_leak.py
    1  harness/scripts/audit/audit_pilot.py
    1  harness/scripts/audit/audit_r4.py
    1  harness/scripts/audit/audit_r4b.py
    1  harness/scripts/audit/audit_r5_ids.py
    1  harness/scripts/audit/audit_r5_scan.py
    1  harness/scripts/audit/audit_round2.py
    1  harness/scripts/audit/audit_round2b.py
    1  harness/scripts/audit/audit_round2c.py
    1  harness/scripts/audit/audit_round2d.py
    1  harness/scripts/audit/audit_steps.py
    2  harness/scripts/audit/audit_v6.py
    2  harness/scripts/audit/case_mem.py
    1  harness/scripts/audit/diff_fn.py
    1  harness/scripts/audit/extract_codex.py
    1  harness/scripts/audit_a5_shared_gates.py
    1  harness/scripts/build_swebench_lite_subset.py
    1  harness/scripts/calibrate_pilot_image_grader.py
    1  harness/scripts/preflight_a5_sources.py
    1  harness/scripts/sprint2_write_dev_tasks.py
    3  harness/src/eval/a5_memory_snapshot.py
    1  harness/src/eval/a5_pilot_lock.py
    1  harness/tests/test_memory_cards.py
```

### `C:\Users\`：71 个文件，142 处

```
    4  agent/benchmarks/a5/memory-cards-v6.jsonl
    1  agent/docs/upgrade/01_coding-harness_总修改目标_v1.0.md
    5  agent/docs/upgrade/A5-PILOT20-STATUS.md
    6  agent/docs/upgrade/A5-VERIFICATION.md
    3  agent/docs/upgrade/H4-ADAPTER.md
    1  agent/docs/upgrade/IMPLEMENTATION-PLAN.md
    8  agent/docs/upgrade/IMPLEMENTED-TP01-04.md
    8  agent/docs/upgrade/VERIFICATION.md
    3  agent/docs/upgrade/tasks/TP01-PUBLIC-BOUNDARY.md
    3  agent/docs/upgrade/tasks/TP02-EVIDENCE-LOCATOR.md
    3  agent/docs/upgrade/tasks/TP03-MEMORY-PROVENANCE.md
    3  agent/docs/upgrade/tasks/TP04-MEMORY-VALIDITY.md
    2  harness/docs/archive/DEMO-SCRIPT.zh-CN.md
    1  harness/docs/archive/SOLID-A-BATCH-EXECUTION.zh-CN.md
    1  harness/docs/archive/SOLID-B-BATCH-EXECUTION.zh-CN.md
    1  harness/docs/archive/SOLID-C-BATCH-EXECUTION.zh-CN.md
    1  harness/docs/archive/SOLID-D1-CONTAMINATION-EXECUTION.zh-CN.md
    6  harness/docs/archive/SOLID-D1-POLISH-EXECUTION.zh-CN.md
    1  harness/docs/archive/SOLID-D1-REWORK-EXECUTION.zh-CN.md
    1  harness/docs/archive/SOLID-D1-SCAFFOLD-EXECUTION.zh-CN.md
    1  harness/docs/archive/SOLID-D1-SWEBENCH-EXECUTION.zh-CN.md
    1  harness/docs/archive/SOLID-D2-CLOSEOUT-EXECUTION.zh-CN.md
    3  harness/docs/archive/SOLID-D2-DEMO-EXECUTION.zh-CN.md
    1  harness/docs/archive/SOLID-D2-REMAINING-EXECUTION.zh-CN.md
    1  harness/docs/changes/CODEX-DEFERRED-GAPS.zh-CN.md
    3  harness/docs/changes/INTERVIEW-FINAL-CLOSEOUT.zh-CN.md
    1  harness/docs/changes/P0-A-CLOSEOUT.zh-CN.md
    2  harness/docs/changes/P1-1-PLANNER-BEHAVIOR.zh-CN.md
    2  harness/docs/changes/P1-2-CONTEXT-L1.zh-CN.md
    2  harness/docs/changes/P1-2-P1-3-CLOSEOUT.zh-CN.md
    3  harness/docs/changes/P1-3-AGENT-AS-TOOL.zh-CN.md
    2  harness/docs/changes/P2-1-LLMCLIENT-ADAPTER-STREAM.zh-CN.md
    1  harness/docs/changes/POLISH-P1-P2-CLOSEOUT.zh-CN.md
    1  harness/docs/changes/SOLID-A-BATCH-CLOSEOUT.zh-CN.md
    1  harness/docs/changes/SOLID-B-BATCH-CLOSEOUT.zh-CN.md
    1  harness/docs/changes/SOLID-C-BATCH-CLOSEOUT.zh-CN.md
    3  harness/docs/changes/SOLID-D1-SWEBENCH-CLOSEOUT.zh-CN.md
    1  harness/docs/publish/AUDIT-P1.zh-CN.md
    3  harness/docs/publish/CHECKPOINT-P1-LOCAL-INFO.md
    4  harness/docs/publish/CHECKPOINT-P1.md
    1  harness/docs/publish/PUBLISH-CONTRACT.zh-CN.md
    1  harness/docs/sprint/HARNESS-CAPABILITY-SPRINT.zh-CN.md
    1  harness/docs/sprint/PROGRESS.md
    1  harness/docs/upgrade/01_coding-harness_总修改目标_v1.0.md
    1  harness/docs/upgrade/A5-HOST-PREFLIGHT-24-CONTRACT.md
    4  harness/docs/upgrade/BASELINE-EVIDENCE.md
    1  harness/docs/upgrade/H3-IMPLEMENTATION.zh-CN.md
    1  harness/docs/upgrade/H5-DEEPSEEK.zh-CN.md
    2  harness/docs/upgrade/IMPLEMENTATION-PLAN.md
    1  harness/docs/upgrade/R2-LITE-TRUE-SUMMARY.zh-CN.md
    1  harness/docs/upgrade/R2-WRAPPER-CONTRACT.zh-CN.md
    1  harness/docs/upgrade/evidence/A5-harness-preflight-25h-repo-baseline-sympy20154/failure-retry-ledger.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-25h-repo-baseline-sympy20154/receipts.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-25h-repo-baseline-sympy20154/tasks/sympy__sympy-20154/receipt.json
    3  harness/docs/upgrade/evidence/A5-harness-preflight-61-history-baseline/failure-retry-ledger.json
    3  harness/docs/upgrade/evidence/A5-harness-preflight-61-history-baseline/receipts.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-61-history-baseline/tasks/pytest-dev__pytest-5103/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-61-history-baseline/tasks/scikit-learn__scikit-learn-10297/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-61-history-baseline/tasks/sympy__sympy-11400/receipt.json
    3  harness/docs/upgrade/evidence/A5-harness-preflight-62-history-baseline/failure-retry-ledger.json
    3  harness/docs/upgrade/evidence/A5-harness-preflight-62-history-baseline/receipts.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-62-history-baseline/tasks/pytest-dev__pytest-5103/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-62-history-baseline/tasks/scikit-learn__scikit-learn-10297/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-62-history-baseline/tasks/sympy__sympy-11400/receipt.json
    1  harness/docs/upgrade/evidence/HP-03/CODEX-ACCEPTANCE-20260919.md
    1  harness/reports/examples/baseline_vs_context_compact_real.md
    1  harness/reports/examples/subagent_readonly_repo_tasks_real.md
    1  harness/scripts/audit/extract_codex.py
    1  harness/scripts/audit/user_msgs.py
    1  harness/scripts/build_swebench_lite_subset.py
    1  harness/scripts/setup_swebench_envs.py
```

### `23500`：53 个文件，81 处

```
    1  agent/docs/upgrade/01_coding-harness_总修改目标_v1.0.md
    1  agent/reports/phase6/20260702_100403/ablation-summary.json
    1  harness/docs/changes/P1-3-AGENT-AS-TOOL.zh-CN.md
    3  harness/docs/publish/CHECKPOINT-P1-LOCAL-INFO.md
    2  harness/docs/publish/CHECKPOINT-P1.md
    1  harness/docs/publish/PUBLISH-CONTRACT.zh-CN.md
    1  harness/docs/sprint/HARNESS-CAPABILITY-SPRINT.zh-CN.md
    1  harness/docs/upgrade/01_coding-harness_总修改目标_v1.0.md
    1  harness/docs/upgrade/A5-HOST-PREFLIGHT-24-CONTRACT.md
    1  harness/docs/upgrade/BASELINE-EVIDENCE.md
    1  harness/docs/upgrade/H3-IMPLEMENTATION.zh-CN.md
    1  harness/docs/upgrade/H5-DEEPSEEK.zh-CN.md
    1  harness/docs/upgrade/IMPLEMENTATION-PLAN.md
    1  harness/docs/upgrade/R2-LITE-TRUE-SUMMARY.zh-CN.md
    1  harness/docs/upgrade/R2-WRAPPER-CONTRACT.zh-CN.md
    1  harness/docs/upgrade/evidence/A5-harness-preflight-53-remaining16-sources/receipts.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-53-remaining16-sources/tasks/pytest-dev__pytest-5221/source-inventory.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-53-remaining16-sources/tasks/pytest-dev__pytest-5227/source-inventory.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-53-remaining16-sources/tasks/scikit-learn__scikit-learn-10949/source-receipt.json
    2  harness/docs/upgrade/evidence/H5-interop/real-04/on/run-result.json
    1  harness/docs/upgrade/evidence/HP-03/CODEX-ACCEPTANCE-20260919.md
    3  harness/tests/fixtures/repos/swebench_sympy__sympy-23117/doc/src/modules/physics/vector/kin_1pt.svg
    1  harness/tests/fixtures/repos/swebench_sympy__sympy-23117/sympy/discrete/tests/test_convolutions.py
    1  harness/tests/fixtures/repos/swebench_sympy__sympy-23117/sympy/matrices/expressions/funcmatrix.py
    2  harness/tests/fixtures/repos/swebench_sympy__sympy-23117/sympy/polys/polyquinticconst.py
    3  harness/tests/fixtures/repos/swebench_sympy__sympy-23191/doc/src/modules/physics/vector/kin_1pt.svg
    1  harness/tests/fixtures/repos/swebench_sympy__sympy-23191/sympy/discrete/tests/test_convolutions.py
    1  harness/tests/fixtures/repos/swebench_sympy__sympy-23191/sympy/matrices/expressions/funcmatrix.py
    2  harness/tests/fixtures/repos/swebench_sympy__sympy-23191/sympy/polys/polyquinticconst.py
    3  harness/tests/fixtures/repos/swebench_sympy__sympy-23262/doc/src/modules/physics/vector/kin_1pt.svg
    1  harness/tests/fixtures/repos/swebench_sympy__sympy-23262/sympy/discrete/tests/test_convolutions.py
    1  harness/tests/fixtures/repos/swebench_sympy__sympy-23262/sympy/matrices/expressions/funcmatrix.py
    2  harness/tests/fixtures/repos/swebench_sympy__sympy-23262/sympy/polys/polyquinticconst.py
    3  harness/tests/fixtures/repos/swebench_sympy__sympy-24066/doc/src/modules/physics/vector/kin_1pt.svg
    1  harness/tests/fixtures/repos/swebench_sympy__sympy-24066/sympy/discrete/tests/test_convolutions.py
    1  harness/tests/fixtures/repos/swebench_sympy__sympy-24066/sympy/matrices/expressions/funcmatrix.py
    2  harness/tests/fixtures/repos/swebench_sympy__sympy-24066/sympy/polys/polyquinticconst.py
    3  harness/tests/fixtures/repos/swebench_sympy__sympy-24102/doc/src/modules/physics/vector/kin_1pt.svg
    1  harness/tests/fixtures/repos/swebench_sympy__sympy-24102/sympy/discrete/tests/test_convolutions.py
    1  harness/tests/fixtures/repos/swebench_sympy__sympy-24102/sympy/matrices/expressions/funcmatrix.py
    2  harness/tests/fixtures/repos/swebench_sympy__sympy-24102/sympy/polys/polyquinticconst.py
    3  harness/tests/fixtures/repos/swebench_sympy__sympy-24152/doc/src/modules/physics/vector/kin_1pt.svg
    1  harness/tests/fixtures/repos/swebench_sympy__sympy-24152/sympy/discrete/tests/test_convolutions.py
    1  harness/tests/fixtures/repos/swebench_sympy__sympy-24152/sympy/matrices/expressions/funcmatrix.py
    2  harness/tests/fixtures/repos/swebench_sympy__sympy-24152/sympy/polys/polyquinticconst.py
    3  harness/tests/fixtures/repos/swebench_sympy__sympy-24213/doc/src/modules/physics/vector/kin_1pt.svg
    1  harness/tests/fixtures/repos/swebench_sympy__sympy-24213/sympy/discrete/tests/test_convolutions.py
    1  harness/tests/fixtures/repos/swebench_sympy__sympy-24213/sympy/matrices/expressions/funcmatrix.py
    2  harness/tests/fixtures/repos/swebench_sympy__sympy-24213/sympy/polys/polyquinticconst.py
    3  harness/tests/fixtures/repos/swebench_sympy__sympy-24909/doc/src/modules/physics/vector/kin_1pt.svg
    1  harness/tests/fixtures/repos/swebench_sympy__sympy-24909/sympy/discrete/tests/test_convolutions.py
    1  harness/tests/fixtures/repos/swebench_sympy__sympy-24909/sympy/matrices/expressions/funcmatrix.py
    2  harness/tests/fixtures/repos/swebench_sympy__sympy-24909/sympy/polys/polyquinticconst.py
```

### `Administrator`：61 个文件，127 处

```
    5  agent/docs/upgrade/A5-PILOT20-STATUS.md
    6  agent/docs/upgrade/A5-VERIFICATION.md
    3  agent/docs/upgrade/H4-ADAPTER.md
    1  agent/docs/upgrade/IMPLEMENTATION-PLAN.md
    8  agent/docs/upgrade/IMPLEMENTED-TP01-04.md
    8  agent/docs/upgrade/VERIFICATION.md
    3  agent/docs/upgrade/tasks/TP01-PUBLIC-BOUNDARY.md
    3  agent/docs/upgrade/tasks/TP02-EVIDENCE-LOCATOR.md
    3  agent/docs/upgrade/tasks/TP03-MEMORY-PROVENANCE.md
    3  agent/docs/upgrade/tasks/TP04-MEMORY-VALIDITY.md
    2  harness/docs/archive/DEMO-SCRIPT.zh-CN.md
    1  harness/docs/archive/SOLID-A-BATCH-EXECUTION.zh-CN.md
    1  harness/docs/archive/SOLID-B-BATCH-EXECUTION.zh-CN.md
    1  harness/docs/archive/SOLID-C-BATCH-EXECUTION.zh-CN.md
    1  harness/docs/archive/SOLID-D1-CONTAMINATION-EXECUTION.zh-CN.md
    6  harness/docs/archive/SOLID-D1-POLISH-EXECUTION.zh-CN.md
    1  harness/docs/archive/SOLID-D1-REWORK-EXECUTION.zh-CN.md
    1  harness/docs/archive/SOLID-D1-SCAFFOLD-EXECUTION.zh-CN.md
    1  harness/docs/archive/SOLID-D1-SWEBENCH-EXECUTION.zh-CN.md
    1  harness/docs/archive/SOLID-D2-CLOSEOUT-EXECUTION.zh-CN.md
    3  harness/docs/archive/SOLID-D2-DEMO-EXECUTION.zh-CN.md
    1  harness/docs/archive/SOLID-D2-REMAINING-EXECUTION.zh-CN.md
    1  harness/docs/changes/CODEX-DEFERRED-GAPS.zh-CN.md
    3  harness/docs/changes/INTERVIEW-FINAL-CLOSEOUT.zh-CN.md
    1  harness/docs/changes/P0-A-CLOSEOUT.zh-CN.md
    2  harness/docs/changes/P1-1-PLANNER-BEHAVIOR.zh-CN.md
    2  harness/docs/changes/P1-2-CONTEXT-L1.zh-CN.md
    2  harness/docs/changes/P1-2-P1-3-CLOSEOUT.zh-CN.md
    2  harness/docs/changes/P1-3-AGENT-AS-TOOL.zh-CN.md
    2  harness/docs/changes/P2-1-LLMCLIENT-ADAPTER-STREAM.zh-CN.md
    1  harness/docs/changes/POLISH-P1-P2-CLOSEOUT.zh-CN.md
    1  harness/docs/changes/SOLID-A-BATCH-CLOSEOUT.zh-CN.md
    1  harness/docs/changes/SOLID-B-BATCH-CLOSEOUT.zh-CN.md
    1  harness/docs/changes/SOLID-C-BATCH-CLOSEOUT.zh-CN.md
    3  harness/docs/changes/SOLID-D1-SWEBENCH-CLOSEOUT.zh-CN.md
    1  harness/docs/publish/AUDIT-P1.zh-CN.md
    3  harness/docs/publish/CHECKPOINT-P1-LOCAL-INFO.md
    4  harness/docs/publish/CHECKPOINT-P1.md
    1  harness/docs/publish/PUBLISH-CONTRACT.zh-CN.md
    1  harness/docs/sprint/PROGRESS.md
    4  harness/docs/upgrade/BASELINE-EVIDENCE.md
    1  harness/docs/upgrade/IMPLEMENTATION-PLAN.md
    1  harness/docs/upgrade/evidence/A5-harness-preflight-25h-repo-baseline-sympy20154/failure-retry-ledger.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-25h-repo-baseline-sympy20154/receipts.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-25h-repo-baseline-sympy20154/tasks/sympy__sympy-20154/receipt.json
    3  harness/docs/upgrade/evidence/A5-harness-preflight-61-history-baseline/failure-retry-ledger.json
    3  harness/docs/upgrade/evidence/A5-harness-preflight-61-history-baseline/receipts.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-61-history-baseline/tasks/pytest-dev__pytest-5103/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-61-history-baseline/tasks/scikit-learn__scikit-learn-10297/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-61-history-baseline/tasks/sympy__sympy-11400/receipt.json
    3  harness/docs/upgrade/evidence/A5-harness-preflight-62-history-baseline/failure-retry-ledger.json
    3  harness/docs/upgrade/evidence/A5-harness-preflight-62-history-baseline/receipts.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-62-history-baseline/tasks/pytest-dev__pytest-5103/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-62-history-baseline/tasks/scikit-learn__scikit-learn-10297/receipt.json
    1  harness/docs/upgrade/evidence/A5-harness-preflight-62-history-baseline/tasks/sympy__sympy-11400/receipt.json
    1  harness/reports/examples/baseline_vs_context_compact_real.md
    1  harness/reports/examples/subagent_readonly_repo_tasks_real.md
    1  harness/scripts/audit/extract_codex.py
    1  harness/scripts/audit/user_msgs.py
    1  harness/scripts/build_swebench_lite_subset.py
    1  harness/scripts/setup_swebench_envs.py
```

## C. 跨仓库或本机绝对路径的代码引用（合同第 1 节，不修）

扫描 HEAD 里的 `.py`、`.yaml`、`.yml`、`.toml`、`.ps1`、`.sh`、`.cfg`、`.ini`（不含 `harness/tests/fixtures/repos/`），匹配 `parent / "coding-agent|coding-harness"`、`../coding-*`、`coding-agent/`、`coding-harness/` 和 `<盘符>:\crq`。共 53 个文件、122 行。

| 文件 | 行号 |
| --- | --- |
| `agent/reposkill_agent/experiments/funding.py` | 258 |
| `agent/scripts/build_memory_cards_v4.py` | 27, 30, 31, 32, 33 |
| `agent/scripts/dev_loo_v4.py` | 14 |
| `agent/scripts/dev_time_selection.py` | 15 |
| `agent/scripts/pilot_selection_v4.py` | 15, 41 |
| `agent/scripts/posthoc_a6_anchor.py` | 5, 6 |
| `agent/tests/test_a6_diff.py` | 21 |
| `agent/tests/test_analyze_a6_retry.py` | 28, 187 |
| `agent/tests/test_event_extract.py` | 10, 201 |
| `agent/tests/test_lightweight_snapshot.py` | 14 |
| `agent/tests/test_memory_cards.py` | 17, 20 |
| `agent/tests/test_memory_cards_v3.py` | 11, 14 |
| `agent/tests/test_memory_cards_v5.py` | 10 |
| `harness/configs/sprint/dev-tasks.yaml` | 11, 27, 41, 59, 73, 87, 101, 115, 129, 143, 157, 171, 185, 199 |
| `harness/configs/sprint/pilot-tasks.yaml` | 8, 9, 77, 78, 169, 170, 216, 217, 242, 243, 257, 258, 272, 273, 471, 472, 680, 681, 695, 696, 755, 756, 850, 851, 866, 867, 881, 882, 896, 897, 911, 912, 954, 955, 978, 993, 994, 1008, 1009 |
| `harness/scripts/a5_memory_source_smoke.py` | 33 |
| `harness/scripts/audit/audit_b0_deltas.py` | 6 |
| `harness/scripts/audit/audit_leak.py` | 5 |
| `harness/scripts/audit/audit_pilot.py` | 5 |
| `harness/scripts/audit/audit_r4.py` | 6 |
| `harness/scripts/audit/audit_r4b.py` | 6 |
| `harness/scripts/audit/audit_r5_ids.py` | 6 |
| `harness/scripts/audit/audit_r5_scan.py` | 6 |
| `harness/scripts/audit/audit_round2.py` | 5 |
| `harness/scripts/audit/audit_round2b.py` | 5 |
| `harness/scripts/audit/audit_round2c.py` | 5 |
| `harness/scripts/audit/audit_round2d.py` | 6 |
| `harness/scripts/audit/audit_steps.py` | 5 |
| `harness/scripts/audit/audit_v6.py` | 6, 7 |
| `harness/scripts/audit/case_mem.py` | 6, 7 |
| `harness/scripts/audit/diff_fn.py` | 5 |
| `harness/scripts/audit/extract_codex.py` | 7 |
| `harness/scripts/audit/user_msgs.py` | 5 |
| `harness/scripts/audit_a5_shared_gates.py` | 22 |
| `harness/scripts/build_swebench_lite_subset.py` | 674, 715 |
| `harness/scripts/calibrate_pilot_image_grader.py` | 44 |
| `harness/scripts/preflight_a5_image_backed.py` | 29 |
| `harness/scripts/preflight_a5_memory_sources.py` | 14 |
| `harness/scripts/preflight_a5_pytest.py` | 24 |
| `harness/scripts/preflight_a5_repo_baseline.py` | 30 |
| `harness/scripts/preflight_a5_sources.py` | 16 |
| `harness/scripts/prepare_a5_typed_tree.py` | 15 |
| `harness/scripts/run_a5_real.py` | 33 |
| `harness/scripts/run_swe_task.py` | 745, 901 |
| `harness/scripts/setup_swebench_envs.py` | 93 |
| `harness/scripts/sprint2_write_dev_tasks.py` | 14 |
| `harness/scripts/sprint5_b2_smoke.py` | 14 |
| `harness/scripts/sprint6_b2_stats.py` | 22 |
| `harness/scripts/sprint6_predict_injection.py` | 105 |
| `harness/scripts/sprint7_inventory.py` | 20, 108, 113 |
| `harness/src/eval/a5_memory_snapshot.py` | 236, 237, 238 |
| `harness/src/eval/a5_pilot_lock.py` | 20 |
| `harness/tests/test_memory_cards.py` | 8 |
