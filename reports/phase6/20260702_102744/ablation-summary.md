# Phase 6 Ablation Summary

Run ID: `20260702_102744`
Generated at: `2026-07-02T10:30:45.740230+00:00`
Task count: `12`
Repeats: `3`
Seed: `42`
Seed memory: `True`
Hard mode: `True`

| Config | success_rate+/-std | avg_steps+/-std | avg_replan+/-std | skill_neg_transfer | memory_useful | memory_stale | role_handoff | roles_used |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| A0_baseline | 0.00+/-0.00 | 1.00+/-0.00 | 0.00+/-0.00 | 0 | 0 | 0 | 0.00 | `['single_agent']` |
| A0_baseline failure taxonomy | `{'test_failure': 36}` |  |  |  |  |  |  |  |
| A1_planner | 0.00+/-0.00 | 6.00+/-0.00 | 1.00+/-0.00 | 0 | 0 | 0 | 0.00 | `['planner_agent']` |
| A1_planner failure taxonomy | `{'test_failure': 36}` |  |  |  |  |  |  |  |
| A2_multi_agent | 0.00+/-0.00 | 6.00+/-0.00 | 1.00+/-0.00 | 0 | 0 | 0 | 5.00 | `['developer', 'locator', 'manager']` |
| A2_multi_agent failure taxonomy | `{'test_failure': 36}` |  |  |  |  |  |  |  |
| A3_skill | 0.92+/-0.00 | 5.08+/-0.00 | 0.08+/-0.00 | 0 | 0 | 0 | 4.08 | `['developer', 'locator', 'manager', 'qa']` |
| A3_skill failure taxonomy | `{'success': 33, 'test_failure': 3}` |  |  |  |  |  |  |  |
| A4_memory | 0.89+/-0.16 | 5.11+/-0.16 | 0.11+/-0.16 | 0 | 32 | 1 | 4.11 | `['developer', 'locator', 'manager', 'qa']` |
| A4_memory failure taxonomy | `{'test_failure': 4, 'success': 32}` |  |  |  |  |  |  |  |
| A5_full | 1.00+/-0.00 | 5.00+/-0.00 | 0.00+/-0.00 | 0 | 35 | 0 | 4.00 | `['developer', 'locator', 'manager', 'qa']` |
| A5_full failure taxonomy | `{'success': 36}` |  |  |  |  |  |  |  |

## By Task Category

| Config | Category | Tasks | Success Rate | Avg Steps | Avg Replan | Main Failure |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| A0_baseline | regression | 9 | 0.00 | 1.00 | 0.00 | test_failure |
| A0_baseline | api | 9 | 0.00 | 1.00 | 0.00 | test_failure |
| A0_baseline | rename | 9 | 0.00 | 1.00 | 0.00 | test_failure |
| A0_baseline | traceback | 9 | 0.00 | 1.00 | 0.00 | test_failure |
| A1_planner | regression | 9 | 0.00 | 6.00 | 1.00 | test_failure |
| A1_planner | api | 9 | 0.00 | 6.00 | 1.00 | test_failure |
| A1_planner | rename | 9 | 0.00 | 6.00 | 1.00 | test_failure |
| A1_planner | traceback | 9 | 0.00 | 6.00 | 1.00 | test_failure |
| A2_multi_agent | regression | 9 | 0.00 | 6.00 | 1.00 | test_failure |
| A2_multi_agent | api | 9 | 0.00 | 6.00 | 1.00 | test_failure |
| A2_multi_agent | rename | 9 | 0.00 | 6.00 | 1.00 | test_failure |
| A2_multi_agent | traceback | 9 | 0.00 | 6.00 | 1.00 | test_failure |
| A3_skill | regression | 9 | 1.00 | 5.00 | 0.00 | success |
| A3_skill | api | 9 | 1.00 | 5.00 | 0.00 | success |
| A3_skill | rename | 9 | 0.67 | 5.33 | 0.33 | success |
| A3_skill | traceback | 9 | 1.00 | 5.00 | 0.00 | success |
| A4_memory | regression | 9 | 0.89 | 5.11 | 0.11 | success |
| A4_memory | api | 9 | 0.89 | 5.11 | 0.11 | success |
| A4_memory | rename | 9 | 0.89 | 5.11 | 0.11 | success |
| A4_memory | traceback | 9 | 0.89 | 5.11 | 0.11 | success |
| A5_full | regression | 9 | 1.00 | 5.00 | 0.00 | success |
| A5_full | api | 9 | 1.00 | 5.00 | 0.00 | success |
| A5_full | rename | 9 | 1.00 | 5.00 | 0.00 | success |
| A5_full | traceback | 9 | 1.00 | 5.00 | 0.00 | success |
