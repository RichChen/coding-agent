# LLM Mechanism Ablation Summary

Run ID: `20260704_005217`
Generated at: `2026-07-04T01:20:04.169520+00:00`
Task count: `12`
Repeats: `1`
Seed: `42`
Mock LLM: `False`

| Config | success_rate+/-std | avg_steps+/-std | llm_calls | parse_err | patch_applied |
| --- | ---: | ---: | ---: | ---: | ---: |
| L2_llm_multi | 0.67+/-0.00 | 6.58+/-0.00 | 20 | 2 | 15 |
| L2_llm_multi failure taxonomy | `{'test_failure': 4, 'success': 8}` |  |  |  |  |
| L4_llm_memory | 0.92+/-0.00 | 6.25+/-0.00 | 16 | 0 | 19 |
| L4_llm_memory failure taxonomy | `{'success': 11, 'test_failure': 1}` |  |  |  |  |
| L5_llm_full | 0.67+/-0.00 | 6.42+/-0.00 | 22 | 4 | 14 |
| L5_llm_full failure taxonomy | `{'success': 8, 'test_failure': 4}` |  |  |  |  |

## Skill / Memory Injection

| Config | skill_cand | skill_inj | skill_gated | mem_cand | mem_inj |
| --- | ---: | ---: | ---: | ---: | ---: |
| L2_llm_multi | 0 | 0 | 0 | 0 | 0 |
| L4_llm_memory | 0 | 0 | 0 | 67 | 40 |
| L5_llm_full | 66 | 2 | 64 | 66 | 10 |

## Augmentation Policy Suppression

| Config | skill_suppressed | mem_suppressed |
| --- | ---: | ---: |
| L2_llm_multi | 0 | 0 |
| L4_llm_memory | 0 | 0 |
| L5_llm_full | 12 | 34 |

## Context Expansion / JSON Repair

| Config | ctx_expand | paths_added | ctx_recovered | repair_try | repair_ok |
| --- | ---: | ---: | ---: | ---: | ---: |
| L2_llm_multi | 2 | 6 | 1 | 1 | 1 |
| L4_llm_memory | 0 | 0 | 0 | 0 | 0 |
| L5_llm_full | 3 | 9 | 2 | 3 | 3 |

## By Task Category

| Config | Category | Tasks | Success Rate | Avg Steps | Main Failure |
| --- | --- | ---: | ---: | ---: | --- |
| L2_llm_multi | context_heavy | 4 | 0.75 | 6.25 | success |
| L2_llm_multi | skill_heavy | 4 | 0.75 | 7.25 | success |
| L2_llm_multi | memory_heavy | 4 | 0.50 | 6.25 | test_failure |
| L4_llm_memory | context_heavy | 4 | 1.00 | 6.00 | success |
| L4_llm_memory | skill_heavy | 4 | 1.00 | 7.00 | success |
| L4_llm_memory | memory_heavy | 4 | 0.75 | 5.75 | success |
| L5_llm_full | context_heavy | 4 | 0.75 | 6.50 | success |
| L5_llm_full | skill_heavy | 4 | 0.75 | 7.25 | success |
| L5_llm_full | memory_heavy | 4 | 0.50 | 5.50 | test_failure |
