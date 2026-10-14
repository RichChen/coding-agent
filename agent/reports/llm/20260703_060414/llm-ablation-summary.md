# LLM Mechanism Ablation Summary

Run ID: `20260703_060414`
Generated at: `2026-07-03T06:07:53.746923+00:00`
Task count: `3`
Repeats: `1`
Seed: `42`
Mock LLM: `False`

| Config | success_rate+/-std | avg_steps+/-std | llm_calls | parse_err | patch_applied |
| --- | ---: | ---: | ---: | ---: | ---: |
| L0_llm_single | 0.67+/-0.00 | 2.00+/-0.00 | 3 | 0 | 2 |
| L0_llm_single failure taxonomy | `{'success': 2, 'test_failure': 1}` |  |  |  |  |
| L1_llm_planner | 0.33+/-0.00 | 5.67+/-0.00 | 2 | 0 | 1 |
| L1_llm_planner failure taxonomy | `{'success': 1, 'test_failure': 2}` |  |  |  |  |
| L2_llm_multi | 0.33+/-0.00 | 5.67+/-0.00 | 2 | 0 | 1 |
| L2_llm_multi failure taxonomy | `{'success': 1, 'test_failure': 2}` |  |  |  |  |
| L3_llm_skill | 0.67+/-0.00 | 5.33+/-0.00 | 2 | 0 | 2 |
| L3_llm_skill failure taxonomy | `{'success': 2, 'test_failure': 1}` |  |  |  |  |
| L4_llm_memory | 0.67+/-0.00 | 5.33+/-0.00 | 2 | 0 | 2 |
| L4_llm_memory failure taxonomy | `{'success': 2, 'test_failure': 1}` |  |  |  |  |
| L5_llm_full | 0.33+/-0.00 | 5.67+/-0.00 | 2 | 0 | 1 |
| L5_llm_full failure taxonomy | `{'success': 1, 'test_failure': 2}` |  |  |  |  |

## By Task Category

| Config | Category | Tasks | Success Rate | Avg Steps | Main Failure |
| --- | --- | ---: | ---: | ---: | --- |
| L0_llm_single | rename | 3 | 0.67 | 2.00 | success |
| L1_llm_planner | rename | 3 | 0.33 | 5.67 | test_failure |
| L2_llm_multi | rename | 3 | 0.33 | 5.67 | test_failure |
| L3_llm_skill | rename | 3 | 0.67 | 5.33 | success |
| L4_llm_memory | rename | 3 | 0.67 | 5.33 | success |
| L5_llm_full | rename | 3 | 0.33 | 5.67 | test_failure |
