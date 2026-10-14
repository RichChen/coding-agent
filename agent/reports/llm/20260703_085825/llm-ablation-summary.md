# LLM Mechanism Ablation Summary

Run ID: `20260703_085825`
Generated at: `2026-07-03T08:58:31.285624+00:00`
Task count: `1`
Repeats: `1`
Seed: `42`
Mock LLM: `True`

| Config | success_rate+/-std | avg_steps+/-std | llm_calls | parse_err | patch_applied |
| --- | ---: | ---: | ---: | ---: | ---: |
| L0_llm_single | 1.00+/-0.00 | 2.00+/-0.00 | 1 | 0 | 1 |
| L0_llm_single failure taxonomy | `{'success': 1}` |  |  |  |  |
| L1_llm_planner | 1.00+/-0.00 | 5.00+/-0.00 | 1 | 0 | 1 |
| L1_llm_planner failure taxonomy | `{'success': 1}` |  |  |  |  |
| L2_llm_multi | 1.00+/-0.00 | 5.00+/-0.00 | 1 | 0 | 1 |
| L2_llm_multi failure taxonomy | `{'success': 1}` |  |  |  |  |
| L3_llm_skill | 1.00+/-0.00 | 5.00+/-0.00 | 1 | 0 | 1 |
| L3_llm_skill failure taxonomy | `{'success': 1}` |  |  |  |  |
| L4_llm_memory | 1.00+/-0.00 | 5.00+/-0.00 | 1 | 0 | 1 |
| L4_llm_memory failure taxonomy | `{'success': 1}` |  |  |  |  |
| L5_llm_full | 1.00+/-0.00 | 5.00+/-0.00 | 1 | 0 | 1 |
| L5_llm_full failure taxonomy | `{'success': 1}` |  |  |  |  |

## By Task Category

| Config | Category | Tasks | Success Rate | Avg Steps | Main Failure |
| --- | --- | ---: | ---: | ---: | --- |
| L0_llm_single | rename | 1 | 1.00 | 2.00 | success |
| L1_llm_planner | rename | 1 | 1.00 | 5.00 | success |
| L2_llm_multi | rename | 1 | 1.00 | 5.00 | success |
| L3_llm_skill | rename | 1 | 1.00 | 5.00 | success |
| L4_llm_memory | rename | 1 | 1.00 | 5.00 | success |
| L5_llm_full | rename | 1 | 1.00 | 5.00 | success |
