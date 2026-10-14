# LLM Mechanism Ablation Summary

Run ID: `20260703_141047`
Generated at: `2026-07-03T14:42:05.961206+00:00`
Task count: `7`
Repeats: `1`
Seed: `42`
Mock LLM: `False`

| Config | success_rate+/-std | avg_steps+/-std | llm_calls | parse_err | patch_applied |
| --- | ---: | ---: | ---: | ---: | ---: |
| L2_llm_multi | 0.86+/-0.00 | 6.57+/-0.00 | 11 | 0 | 7 |
| L2_llm_multi failure taxonomy | `{'test_failure': 1, 'success': 6}` |  |  |  |  |
| L4_llm_memory | 0.86+/-0.00 | 6.29+/-0.00 | 10 | 0 | 10 |
| L4_llm_memory failure taxonomy | `{'success': 6, 'test_failure': 1}` |  |  |  |  |
| L5_llm_full | 0.86+/-0.00 | 6.29+/-0.00 | 11 | 1 | 10 |
| L5_llm_full failure taxonomy | `{'success': 6, 'test_failure': 1}` |  |  |  |  |

## Skill / Memory Injection

| Config | skill_cand | skill_inj | skill_gated | mem_cand | mem_inj |
| --- | ---: | ---: | ---: | ---: | ---: |
| L2_llm_multi | 0 | 0 | 0 | 0 | 0 |
| L4_llm_memory | 0 | 0 | 0 | 79 | 30 |
| L5_llm_full | 23 | 0 | 23 | 82 | 29 |

## Augmentation Policy Suppression

| Config | skill_suppressed | mem_suppressed |
| --- | ---: | ---: |
| L2_llm_multi | 0 | 0 |
| L4_llm_memory | 0 | 0 |
| L5_llm_full | 4 | 1 |

## Context Expansion / JSON Repair

| Config | ctx_expand | paths_added | ctx_recovered | repair_try | repair_ok |
| --- | ---: | ---: | ---: | ---: | ---: |
| L2_llm_multi | 3 | 9 | 2 | 0 | 0 |
| L4_llm_memory | 2 | 6 | 2 | 0 | 0 |
| L5_llm_full | 1 | 3 | 1 | 1 | 1 |

## By Task Category

| Config | Category | Tasks | Success Rate | Avg Steps | Main Failure |
| --- | --- | ---: | ---: | ---: | --- |
| L2_llm_multi | memory_heavy | 7 | 0.86 | 6.57 | success |
| L4_llm_memory | memory_heavy | 7 | 0.86 | 6.29 | success |
| L5_llm_full | memory_heavy | 7 | 0.86 | 6.29 | success |
