# LLM Mechanism Ablation Summary

Run ID: `20260704_060542`
Generated at: `2026-07-04T06:23:28.496215+00:00`
Task count: `6`
Repeats: `1`
Seed: `42`
Mock LLM: `False`

| Config | success_rate+/-std | avg_steps+/-std | llm_calls | parse_err | patch_applied |
| --- | ---: | ---: | ---: | ---: | ---: |
| L0_llm_single | 0.17+/-0.00 | 2.00+/-0.00 | 6 | 0 | 3 |
| L0_llm_single failure taxonomy | `{'test_failure': 5, 'success': 1}` |  |  |  |  |
| L2_llm_multi | 0.67+/-0.00 | 6.83+/-0.00 | 10 | 0 | 10 |
| L2_llm_multi failure taxonomy | `{'success': 4, 'test_failure': 2}` |  |  |  |  |
| L5_llm_full | 0.50+/-0.00 | 7.33+/-0.00 | 12 | 1 | 10 |
| L5_llm_full failure taxonomy | `{'test_failure': 3, 'success': 3}` |  |  |  |  |

## Skill / Memory Injection

| Config | skill_cand | skill_inj | skill_gated | mem_cand | mem_inj |
| --- | ---: | ---: | ---: | ---: | ---: |
| L0_llm_single | 0 | 0 | 0 | 0 | 0 |
| L2_llm_multi | 0 | 0 | 0 | 0 | 0 |
| L5_llm_full | 39 | 2 | 37 | 75 | 12 |

## Augmentation Policy Suppression

| Config | skill_suppressed | mem_suppressed |
| --- | ---: | ---: |
| L0_llm_single | 0 | 0 |
| L2_llm_multi | 0 | 0 |
| L5_llm_full | 12 | 21 |

## Context Expansion / JSON Repair

| Config | ctx_expand | paths_added | ctx_recovered | repair_try | repair_ok |
| --- | ---: | ---: | ---: | ---: | ---: |
| L0_llm_single | 0 | 0 | 0 | 0 | 0 |
| L2_llm_multi | 2 | 6 | 1 | 0 | 0 |
| L5_llm_full | 2 | 6 | 2 | 1 | 1 |

## By Task Category

| Config | Category | Tasks | Success Rate | Avg Steps | Main Failure |
| --- | --- | ---: | ---: | ---: | --- |
| L0_llm_single | memory_heavy | 2 | 0.00 | 2.00 | test_failure |
| L0_llm_single | skill_heavy | 2 | 0.00 | 2.00 | test_failure |
| L0_llm_single | context_heavy | 2 | 0.50 | 2.00 | success |
| L2_llm_multi | memory_heavy | 2 | 0.50 | 6.50 | success |
| L2_llm_multi | skill_heavy | 2 | 0.50 | 7.00 | test_failure |
| L2_llm_multi | context_heavy | 2 | 1.00 | 7.00 | success |
| L5_llm_full | memory_heavy | 2 | 0.00 | 8.00 | test_failure |
| L5_llm_full | skill_heavy | 2 | 1.00 | 6.50 | success |
| L5_llm_full | context_heavy | 2 | 0.50 | 7.50 | success |
