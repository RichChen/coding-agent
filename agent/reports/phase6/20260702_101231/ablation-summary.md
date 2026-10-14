# Phase 6 Ablation Summary

Run ID: `20260702_101231`
Generated at: `2026-07-02T10:13:34.882447+00:00`
Task count: `12`
Repeats: `1`
Seed: `42`
Seed memory: `False`
Hard mode: `True`

| Config | success_rate+/-std | avg_steps+/-std | avg_replan+/-std | skill_neg_transfer | memory_useful | memory_stale | role_handoff | roles_used |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| A0_baseline | 0.00+/-0.00 | 1.00+/-0.00 | 0.00+/-0.00 | 0 | 0 | 0 | 0.00 | `['single_agent']` |
| A0_baseline failure taxonomy | `{'test_failure': 12}` |  |  |  |  |  |  |  |
| A1_planner | 0.00+/-0.00 | 6.00+/-0.00 | 1.00+/-0.00 | 0 | 0 | 0 | 0.00 | `['planner_agent']` |
| A1_planner failure taxonomy | `{'test_failure': 12}` |  |  |  |  |  |  |  |
| A2_multi_agent | 0.00+/-0.00 | 6.00+/-0.00 | 1.00+/-0.00 | 0 | 0 | 0 | 5.00 | `['developer', 'locator', 'manager']` |
| A2_multi_agent failure taxonomy | `{'test_failure': 12}` |  |  |  |  |  |  |  |
| A3_skill | 0.92+/-0.00 | 5.08+/-0.00 | 0.08+/-0.00 | 0 | 0 | 0 | 4.08 | `['developer', 'locator', 'manager', 'qa']` |
| A3_skill failure taxonomy | `{'success': 11, 'test_failure': 1}` |  |  |  |  |  |  |  |
| A4_memory | 0.67+/-0.00 | 5.33+/-0.00 | 0.33+/-0.00 | 0 | 8 | 1 | 4.33 | `['developer', 'locator', 'manager', 'qa']` |
| A4_memory failure taxonomy | `{'test_failure': 4, 'success': 8}` |  |  |  |  |  |  |  |
| A5_full | 1.00+/-0.00 | 5.00+/-0.00 | 0.00+/-0.00 | 0 | 11 | 0 | 4.00 | `['developer', 'locator', 'manager', 'qa']` |
| A5_full failure taxonomy | `{'success': 12}` |  |  |  |  |  |  |  |

## By Task Category

| Config | Category | Tasks | Success Rate | Avg Steps | Avg Replan | Main Failure |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| A0_baseline | regression | 3 | 0.00 | 1.00 | 0.00 | test_failure |
| A0_baseline | api | 3 | 0.00 | 1.00 | 0.00 | test_failure |
| A0_baseline | rename | 3 | 0.00 | 1.00 | 0.00 | test_failure |
| A0_baseline | traceback | 3 | 0.00 | 1.00 | 0.00 | test_failure |
| A1_planner | regression | 3 | 0.00 | 6.00 | 1.00 | test_failure |
| A1_planner | api | 3 | 0.00 | 6.00 | 1.00 | test_failure |
| A1_planner | rename | 3 | 0.00 | 6.00 | 1.00 | test_failure |
| A1_planner | traceback | 3 | 0.00 | 6.00 | 1.00 | test_failure |
| A2_multi_agent | regression | 3 | 0.00 | 6.00 | 1.00 | test_failure |
| A2_multi_agent | api | 3 | 0.00 | 6.00 | 1.00 | test_failure |
| A2_multi_agent | rename | 3 | 0.00 | 6.00 | 1.00 | test_failure |
| A2_multi_agent | traceback | 3 | 0.00 | 6.00 | 1.00 | test_failure |
| A3_skill | regression | 3 | 1.00 | 5.00 | 0.00 | success |
| A3_skill | api | 3 | 1.00 | 5.00 | 0.00 | success |
| A3_skill | rename | 3 | 0.67 | 5.33 | 0.33 | success |
| A3_skill | traceback | 3 | 1.00 | 5.00 | 0.00 | success |
| A4_memory | regression | 3 | 0.67 | 5.33 | 0.33 | success |
| A4_memory | api | 3 | 0.67 | 5.33 | 0.33 | success |
| A4_memory | rename | 3 | 0.67 | 5.33 | 0.33 | success |
| A4_memory | traceback | 3 | 0.67 | 5.33 | 0.33 | success |
| A5_full | regression | 3 | 1.00 | 5.00 | 0.00 | success |
| A5_full | api | 3 | 1.00 | 5.00 | 0.00 | success |
| A5_full | rename | 3 | 1.00 | 5.00 | 0.00 | success |
| A5_full | traceback | 3 | 1.00 | 5.00 | 0.00 | success |
