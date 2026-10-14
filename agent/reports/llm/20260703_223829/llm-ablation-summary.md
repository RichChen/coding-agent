# LLM Mechanism Ablation Summary

Run ID: `20260703_223829`
Generated at: `2026-07-03T22:57:24.302520+00:00`
Task count: `12`
Repeats: `1`
Seed: `42`
Mock LLM: `False`

| Config | success_rate+/-std | avg_steps+/-std | llm_calls | parse_err | patch_applied |
| --- | ---: | ---: | ---: | ---: | ---: |
| L0_llm_single | 0.50+/-0.00 | 2.00+/-0.00 | 13 | 1 | 11 |
| L0_llm_single failure taxonomy | `{'test_failure': 6, 'success': 6}` |  |  |  |  |
| L2_llm_multi | 0.83+/-0.00 | 7.00+/-0.00 | 19 | 0 | 21 |
| L2_llm_multi failure taxonomy | `{'success': 10, 'test_failure': 2}` |  |  |  |  |
| L5_llm_full | 0.92+/-0.00 | 5.92+/-0.00 | 18 | 2 | 18 |
| L5_llm_full failure taxonomy | `{'success': 11, 'test_failure': 1}` |  |  |  |  |

## Skill / Memory Injection

| Config | skill_cand | skill_inj | skill_gated | mem_cand | mem_inj |
| --- | ---: | ---: | ---: | ---: | ---: |
| L0_llm_single | 0 | 0 | 0 | 0 | 0 |
| L2_llm_multi | 0 | 0 | 0 | 0 | 0 |
| L5_llm_full | 56 | 3 | 53 | 57 | 14 |

## Augmentation Policy Suppression

| Config | skill_suppressed | mem_suppressed |
| --- | ---: | ---: |
| L0_llm_single | 0 | 0 |
| L2_llm_multi | 0 | 0 |
| L5_llm_full | 9 | 23 |

## Context Expansion / JSON Repair

| Config | ctx_expand | paths_added | ctx_recovered | repair_try | repair_ok |
| --- | ---: | ---: | ---: | ---: | ---: |
| L0_llm_single | 0 | 0 | 0 | 0 | 0 |
| L2_llm_multi | 2 | 6 | 2 | 0 | 0 |
| L5_llm_full | 1 | 3 | 2 | 2 | 2 |

## By Task Category

| Config | Category | Tasks | Success Rate | Avg Steps | Main Failure |
| --- | --- | ---: | ---: | ---: | --- |
| L0_llm_single | context_heavy | 4 | 0.50 | 2.00 | test_failure |
| L0_llm_single | skill_heavy | 4 | 0.25 | 2.00 | test_failure |
| L0_llm_single | memory_heavy | 4 | 0.75 | 2.00 | success |
| L2_llm_multi | context_heavy | 4 | 1.00 | 7.00 | success |
| L2_llm_multi | skill_heavy | 4 | 1.00 | 7.75 | success |
| L2_llm_multi | memory_heavy | 4 | 0.50 | 6.25 | test_failure |
| L5_llm_full | context_heavy | 4 | 1.00 | 6.75 | success |
| L5_llm_full | skill_heavy | 4 | 1.00 | 5.75 | success |
| L5_llm_full | memory_heavy | 4 | 0.75 | 5.25 | success |
