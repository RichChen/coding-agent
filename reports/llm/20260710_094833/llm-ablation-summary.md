# LLM Mechanism Ablation Summary

Run ID: `20260710_094833`
Generated at: `2026-07-10T09:58:54.905065+00:00`
Task count: `6`
Repeats: `1`
Seed: `42`
Mock LLM: `False`

| Config | success_rate+/-std | avg_steps+/-std | llm_calls | parse_err | patch_applied |
| --- | ---: | ---: | ---: | ---: | ---: |
| L2_llm_multi | 1.00+/-0.00 | 7.67+/-0.00 | 10 | 0 | 10 |
| L2_llm_multi failure taxonomy | `{'success': 6}` |  |  |  |  |
| L5_llm_full | 0.50+/-0.00 | 6.17+/-0.00 | 10 | 0 | 4 |
| L5_llm_full failure taxonomy | `{'success': 3, 'test_failure': 3}` |  |  |  |  |

## Skill / Memory Injection

| Config | skill_cand | skill_inj | skill_gated | mem_cand | mem_inj |
| --- | ---: | ---: | ---: | ---: | ---: |
| L2_llm_multi | 0 | 0 | 0 | 0 | 0 |
| L5_llm_full | 19 | 2 | 17 | 61 | 9 |

## Augmentation Policy Suppression

| Config | skill_suppressed | mem_suppressed |
| --- | ---: | ---: |
| L2_llm_multi | 0 | 0 |
| L5_llm_full | 4 | 19 |

## Context Expansion / JSON Repair

| Config | ctx_expand | paths_added | ctx_recovered | repair_try | repair_ok |
| --- | ---: | ---: | ---: | ---: | ---: |
| L2_llm_multi | 0 | 0 | 0 | 0 | 0 |
| L5_llm_full | 1 | 3 | 0 | 0 | 0 |

## By Task Category

| Config | Category | Tasks | Success Rate | Avg Steps | Main Failure |
| --- | --- | ---: | ---: | ---: | --- |
| L2_llm_multi | memory_heavy | 2 | 1.00 | 7.00 | success |
| L2_llm_multi | context_heavy | 1 | 1.00 | 5.00 | success |
| L2_llm_multi | multi_file_api | 1 | 1.00 | 9.00 | success |
| L2_llm_multi | skill_heavy | 1 | 1.00 | 9.00 | success |
| L2_llm_multi | traceback_repair | 1 | 1.00 | 9.00 | success |
| L5_llm_full | memory_heavy | 2 | 1.00 | 7.00 | success |
| L5_llm_full | context_heavy | 1 | 1.00 | 5.00 | success |
| L5_llm_full | multi_file_api | 1 | 0.00 | 6.00 | test_failure |
| L5_llm_full | skill_heavy | 1 | 0.00 | 6.00 | test_failure |
| L5_llm_full | traceback_repair | 1 | 0.00 | 6.00 | test_failure |
