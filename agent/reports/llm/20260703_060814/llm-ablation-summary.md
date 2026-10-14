# LLM Mechanism Ablation Summary

Run ID: `20260703_060814`
Generated at: `2026-07-03T06:15:15.088915+00:00`
Task count: `12`
Repeats: `1`
Seed: `42`
Mock LLM: `False`

| Config | success_rate+/-std | avg_steps+/-std | llm_calls | parse_err | patch_applied |
| --- | ---: | ---: | ---: | ---: | ---: |
| L0_llm_single | 0.50+/-0.00 | 2.00+/-0.00 | 12 | 0 | 8 |
| L0_llm_single failure taxonomy | `{'success': 6, 'test_failure': 6}` |  |  |  |  |
| L1_llm_planner | 0.00+/-0.00 | 6.08+/-0.00 | 2 | 1 | 1 |
| L1_llm_planner failure taxonomy | `{'test_failure': 12}` |  |  |  |  |
| L2_llm_multi | 0.08+/-0.00 | 5.92+/-0.00 | 2 | 0 | 1 |
| L2_llm_multi failure taxonomy | `{'success': 1, 'test_failure': 11}` |  |  |  |  |
| L3_llm_skill | 0.08+/-0.00 | 6.25+/-0.00 | 2 | 0 | 2 |
| L3_llm_skill failure taxonomy | `{'success': 1, 'test_failure': 11}` |  |  |  |  |
| L4_llm_memory | 0.08+/-0.00 | 6.25+/-0.00 | 2 | 0 | 2 |
| L4_llm_memory failure taxonomy | `{'success': 1, 'test_failure': 11}` |  |  |  |  |
| L5_llm_full | 0.08+/-0.00 | 5.92+/-0.00 | 2 | 0 | 1 |
| L5_llm_full failure taxonomy | `{'success': 1, 'test_failure': 11}` |  |  |  |  |

## By Task Category

| Config | Category | Tasks | Success Rate | Avg Steps | Main Failure |
| --- | --- | ---: | ---: | ---: | --- |
| L0_llm_single | regression | 3 | 0.67 | 2.00 | success |
| L0_llm_single | api | 3 | 0.00 | 2.00 | test_failure |
| L0_llm_single | rename | 3 | 0.67 | 2.00 | success |
| L0_llm_single | traceback | 3 | 0.67 | 2.00 | success |
| L1_llm_planner | regression | 3 | 0.00 | 6.33 | test_failure |
| L1_llm_planner | api | 3 | 0.00 | 6.00 | test_failure |
| L1_llm_planner | rename | 3 | 0.00 | 6.00 | test_failure |
| L1_llm_planner | traceback | 3 | 0.00 | 6.00 | test_failure |
| L2_llm_multi | regression | 3 | 0.33 | 5.67 | test_failure |
| L2_llm_multi | api | 3 | 0.00 | 6.00 | test_failure |
| L2_llm_multi | rename | 3 | 0.00 | 6.00 | test_failure |
| L2_llm_multi | traceback | 3 | 0.00 | 6.00 | test_failure |
| L3_llm_skill | regression | 3 | 0.33 | 7.00 | test_failure |
| L3_llm_skill | api | 3 | 0.00 | 6.00 | test_failure |
| L3_llm_skill | rename | 3 | 0.00 | 6.00 | test_failure |
| L3_llm_skill | traceback | 3 | 0.00 | 6.00 | test_failure |
| L4_llm_memory | regression | 3 | 0.33 | 7.00 | test_failure |
| L4_llm_memory | api | 3 | 0.00 | 6.00 | test_failure |
| L4_llm_memory | rename | 3 | 0.00 | 6.00 | test_failure |
| L4_llm_memory | traceback | 3 | 0.00 | 6.00 | test_failure |
| L5_llm_full | regression | 3 | 0.33 | 5.67 | test_failure |
| L5_llm_full | api | 3 | 0.00 | 6.00 | test_failure |
| L5_llm_full | rename | 3 | 0.00 | 6.00 | test_failure |
| L5_llm_full | traceback | 3 | 0.00 | 6.00 | test_failure |
