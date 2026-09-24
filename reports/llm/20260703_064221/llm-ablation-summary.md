# LLM Mechanism Ablation Summary

Run ID: `20260703_064221`
Generated at: `2026-07-03T07:07:37.546766+00:00`
Task count: `12`
Repeats: `1`
Seed: `42`
Mock LLM: `False`

| Config | success_rate+/-std | avg_steps+/-std | llm_calls | parse_err | patch_applied |
| --- | ---: | ---: | ---: | ---: | ---: |
| L1_llm_planner | 0.92+/-0.00 | 6.33+/-0.00 | 17 | 0 | 14 |
| L1_llm_planner failure taxonomy | `{'success': 11, 'test_failure': 1}` |  |  |  |  |
| L2_llm_multi | 0.92+/-0.00 | 6.25+/-0.00 | 17 | 0 | 13 |
| L2_llm_multi failure taxonomy | `{'success': 11, 'test_failure': 1}` |  |  |  |  |
| L3_llm_skill | 0.67+/-0.00 | 6.33+/-0.00 | 19 | 0 | 11 |
| L3_llm_skill failure taxonomy | `{'test_failure': 4, 'success': 8}` |  |  |  |  |
| L4_llm_memory | 0.58+/-0.00 | 6.25+/-0.00 | 19 | 2 | 11 |
| L4_llm_memory failure taxonomy | `{'success': 7, 'test_failure': 5}` |  |  |  |  |
| L5_llm_full | 0.75+/-0.00 | 6.83+/-0.00 | 20 | 3 | 13 |
| L5_llm_full failure taxonomy | `{'success': 9, 'test_failure': 3}` |  |  |  |  |

## By Task Category

| Config | Category | Tasks | Success Rate | Avg Steps | Main Failure |
| --- | --- | ---: | ---: | ---: | --- |
| L1_llm_planner | regression | 3 | 1.00 | 6.33 | success |
| L1_llm_planner | api | 3 | 0.67 | 8.00 | success |
| L1_llm_planner | rename | 3 | 1.00 | 6.00 | success |
| L1_llm_planner | traceback | 3 | 1.00 | 5.00 | success |
| L2_llm_multi | regression | 3 | 1.00 | 6.33 | success |
| L2_llm_multi | api | 3 | 0.67 | 6.67 | success |
| L2_llm_multi | rename | 3 | 1.00 | 6.00 | success |
| L2_llm_multi | traceback | 3 | 1.00 | 6.00 | success |
| L3_llm_skill | regression | 3 | 0.33 | 7.00 | test_failure |
| L3_llm_skill | api | 3 | 0.67 | 8.00 | success |
| L3_llm_skill | rename | 3 | 1.00 | 5.00 | success |
| L3_llm_skill | traceback | 3 | 0.67 | 5.33 | success |
| L4_llm_memory | regression | 3 | 0.67 | 7.00 | success |
| L4_llm_memory | api | 3 | 0.33 | 7.33 | test_failure |
| L4_llm_memory | rename | 3 | 0.67 | 5.33 | success |
| L4_llm_memory | traceback | 3 | 0.67 | 5.33 | success |
| L5_llm_full | regression | 3 | 0.67 | 8.00 | success |
| L5_llm_full | api | 3 | 0.67 | 8.00 | success |
| L5_llm_full | rename | 3 | 0.67 | 5.33 | success |
| L5_llm_full | traceback | 3 | 1.00 | 6.00 | success |
