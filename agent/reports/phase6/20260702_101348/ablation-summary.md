# Phase 6 Ablation Summary

Run ID: `20260702_101348`
Generated at: `2026-07-02T10:19:26.367786+00:00`
Task count: `24`
Repeats: `3`
Seed: `42`
Seed memory: `False`
Hard mode: `False`

| Config | success_rate+/-std | avg_steps+/-std | avg_replan+/-std | skill_neg_transfer | memory_useful | memory_stale | role_handoff | roles_used |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| A0_baseline | 1.00+/-0.00 | 2.00+/-0.00 | 0.00+/-0.00 | 0 | 0 | 0 | 0.00 | `['single_agent']` |
| A0_baseline failure taxonomy | `{'success': 72}` |  |  |  |  |  |  |  |
| A1_planner | 1.00+/-0.00 | 5.00+/-0.00 | 0.00+/-0.00 | 0 | 0 | 0 | 0.00 | `['planner_agent']` |
| A1_planner failure taxonomy | `{'success': 72}` |  |  |  |  |  |  |  |
| A2_multi_agent | 1.00+/-0.00 | 5.00+/-0.00 | 0.00+/-0.00 | 0 | 0 | 0 | 4.00 | `['developer', 'locator', 'manager', 'qa']` |
| A2_multi_agent failure taxonomy | `{'success': 72}` |  |  |  |  |  |  |  |
| A3_skill | 1.00+/-0.00 | 5.00+/-0.00 | 0.00+/-0.00 | 0 | 0 | 0 | 4.00 | `['developer', 'locator', 'manager', 'qa']` |
| A3_skill failure taxonomy | `{'success': 72}` |  |  |  |  |  |  |  |
| A4_memory | 1.00+/-0.00 | 5.00+/-0.00 | 0.00+/-0.00 | 0 | 69 | 0 | 4.00 | `['developer', 'locator', 'manager', 'qa']` |
| A4_memory failure taxonomy | `{'success': 72}` |  |  |  |  |  |  |  |
| A5_full | 1.00+/-0.00 | 5.00+/-0.00 | 0.00+/-0.00 | 0 | 69 | 0 | 4.00 | `['developer', 'locator', 'manager', 'qa']` |
| A5_full failure taxonomy | `{'success': 72}` |  |  |  |  |  |  |  |

## By Task Category

| Config | Category | Tasks | Success Rate | Avg Steps | Avg Replan | Main Failure |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| A0_baseline | logic | 24 | 1.00 | 2.00 | 0.00 | success |
| A0_baseline | import | 24 | 1.00 | 2.00 | 0.00 | success |
| A0_baseline | feature | 24 | 1.00 | 2.00 | 0.00 | success |
| A1_planner | logic | 24 | 1.00 | 5.00 | 0.00 | success |
| A1_planner | import | 24 | 1.00 | 5.00 | 0.00 | success |
| A1_planner | feature | 24 | 1.00 | 5.00 | 0.00 | success |
| A2_multi_agent | logic | 24 | 1.00 | 5.00 | 0.00 | success |
| A2_multi_agent | import | 24 | 1.00 | 5.00 | 0.00 | success |
| A2_multi_agent | feature | 24 | 1.00 | 5.00 | 0.00 | success |
| A3_skill | logic | 24 | 1.00 | 5.00 | 0.00 | success |
| A3_skill | import | 24 | 1.00 | 5.00 | 0.00 | success |
| A3_skill | feature | 24 | 1.00 | 5.00 | 0.00 | success |
| A4_memory | logic | 24 | 1.00 | 5.00 | 0.00 | success |
| A4_memory | import | 24 | 1.00 | 5.00 | 0.00 | success |
| A4_memory | feature | 24 | 1.00 | 5.00 | 0.00 | success |
| A5_full | logic | 24 | 1.00 | 5.00 | 0.00 | success |
| A5_full | import | 24 | 1.00 | 5.00 | 0.00 | success |
| A5_full | feature | 24 | 1.00 | 5.00 | 0.00 | success |
