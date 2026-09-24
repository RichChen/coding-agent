# A5 initial 24 measured host preflight (host-private evidence)

Ready: 4/24. Source snapshots: 24/24. Model calls: 0; paid: false.

| Task | Role | Full source files / bytes | Collection | Baseline | Grader | Status / reason |
| --- | --- | --- | --- | --- | --- | --- |
| django__django-13265 | target | 6393 / 38513500 | not run | not_run | not_run | invalid_env: full_source_exceeds_runtime_limits |
| django__django-15781 | target | 6637 / 41586843 | not run | not_run | not_run | invalid_env: full_source_exceeds_runtime_limits |
| django__django-13590 | target | 6412 / 38713009 | not run | not_run | not_run | invalid_env: full_source_exceeds_runtime_limits |
| django__django-13448 | target | 6400 / 38637667 | not run | not_run | not_run | invalid_env: full_source_exceeds_runtime_limits |
| sympy__sympy-20154 | target | 1813 / 32900772 | not run | not_run | not_run | invalid_env: full_source_exceeds_runtime_limits |
| sympy__sympy-24152 | target | 1995 / 36513507 | not run | not_run | not_run | invalid_env: full_source_exceeds_runtime_limits |
| sympy__sympy-20442 | target | 1815 / 32961753 | not run | not_run | not_run | invalid_env: full_source_exceeds_runtime_limits |
| sympy__sympy-18532 | target | 1742 / 31938205 | not run | not_run | not_run | invalid_env: full_source_exceeds_runtime_limits |
| scikit-learn__scikit-learn-25747 | target | 1522 / 20731203 | not run | not_run | not_run | invalid_env: full_source_exceeds_runtime_limits |
| scikit-learn__scikit-learn-25500 | target | 1532 / 20682366 | not run | not_run | not_run | invalid_env: full_source_exceeds_runtime_limits |
| scikit-learn__scikit-learn-25638 | target | 1521 / 20712406 | not run | not_run | not_run | invalid_env: full_source_exceeds_runtime_limits |
| scikit-learn__scikit-learn-25570 | target | 1523 / 20691076 | not run | not_run | not_run | invalid_env: full_source_exceeds_runtime_limits |
| pytest-dev__pytest-8365 | target | 535 / 4337617 | 3050 | baseline_fail | pass | ready: all_preflight_checks_passed |
| pytest-dev__pytest-7432 | target | 541 / 3731202 | 2957 | not_run | not_run | grader_unavailable: benchmark_nodeids_not_in_full_collection |
| pytest-dev__pytest-9359 | target | 622 / 4570658 | 3144 | baseline_fail | pass | ready: all_preflight_checks_passed |
| pytest-dev__pytest-7220 | target | 512 / 3591593 | 2842 | baseline_fail | pass | ready: all_preflight_checks_passed |
| sphinx-doc__sphinx-10451 | target | 1599 / 17835140 | not run | not_run | not_run | invalid_env: full_source_exceeds_runtime_limits |
| sphinx-doc__sphinx-8721 | target | 1473 / 16466026 | not run | not_run | not_run | invalid_env: full_source_exceeds_runtime_limits |
| sphinx-doc__sphinx-8595 | target | 1464 / 16428590 | not run | not_run | not_run | invalid_env: full_source_exceeds_runtime_limits |
| sphinx-doc__sphinx-8713 | target | 1467 / 16366995 | not run | not_run | not_run | invalid_env: full_source_exceeds_runtime_limits |
| django__django-10914 | preflight_history_candidate | 6054 / 36070365 | not run | not_run | not_run | invalid_env: full_source_exceeds_runtime_limits |
| sympy__sympy-11400 | preflight_history_candidate | 1401 / 18059667 | not run | not_run | not_run | invalid_env: full_source_exceeds_runtime_limits |
| scikit-learn__scikit-learn-10297 | preflight_history_candidate | 1105 / 15147428 | not run | not_run | not_run | invalid_env: full_source_exceeds_runtime_limits |
| pytest-dev__pytest-5103 | preflight_history_candidate | 418 / 3161090 | 2411 | baseline_fail | pass | ready: all_preflight_checks_passed |

All 19 over-limit source archives are retained intact. They did not enter Docker testing.
Every source must remain within 8 MiB / 2048 files under this execution contract; no image-backed bypass or trimming.
Pytest uses its own candidate source import, pinned task images, complete upstream-configured testing collection,
private test/gold calibration, negative rejection and verified cleanup. Missing canonical node IDs are not guessed.
The remaining 16 memory sources are not started because the initial24 gate did not pass.
No ready preflight row authorizes paid build/pilot. Shared budget/model/price/fingerprint/receipt gates remain blocked.
