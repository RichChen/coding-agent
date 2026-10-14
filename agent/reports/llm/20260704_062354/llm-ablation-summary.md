# LLM Mechanism Ablation Summary

Run ID: `20260704_062354`
Generated at: `2026-07-04T08:12:35.041218+00:00`
Task count: `48`
Repeats: `1`
Seed: `42`
Mock LLM: `False`

| Config | success_rate+/-std | avg_steps+/-std | llm_calls | parse_err | patch_applied |
| --- | ---: | ---: | ---: | ---: | ---: |
| L0_llm_single | 0.48+/-0.00 | 2.00+/-0.00 | 50 | 2 | 38 |
| L0_llm_single failure taxonomy | `{'test_failure': 25, 'success': 23}` |  |  |  |  |
| L2_llm_multi | 0.69+/-0.00 | 6.46+/-0.00 | 79 | 5 | 60 |
| L2_llm_multi failure taxonomy | `{'test_failure': 15, 'success': 33}` |  |  |  |  |
| L5_llm_full | 0.79+/-0.00 | 6.54+/-0.00 | 75 | 1 | 58 |
| L5_llm_full failure taxonomy | `{'success': 38, 'test_failure': 10}` |  |  |  |  |

## Skill / Memory Injection

| Config | skill_cand | skill_inj | skill_gated | mem_cand | mem_inj |
| --- | ---: | ---: | ---: | ---: | ---: |
| L0_llm_single | 0 | 0 | 0 | 0 | 0 |
| L2_llm_multi | 0 | 0 | 0 | 0 | 0 |
| L5_llm_full | 279 | 8 | 271 | 596 | 79 |

## Augmentation Policy Suppression

| Config | skill_suppressed | mem_suppressed |
| --- | ---: | ---: |
| L0_llm_single | 0 | 0 |
| L2_llm_multi | 0 | 0 |
| L5_llm_full | 46 | 129 |

## Context Expansion / JSON Repair

| Config | ctx_expand | paths_added | ctx_recovered | repair_try | repair_ok |
| --- | ---: | ---: | ---: | ---: | ---: |
| L0_llm_single | 0 | 0 | 0 | 0 | 0 |
| L2_llm_multi | 10 | 30 | 2 | 5 | 5 |
| L5_llm_full | 10 | 30 | 4 | 1 | 1 |

## By Task Category

| Config | Category | Tasks | Success Rate | Avg Steps | Main Failure |
| --- | --- | ---: | ---: | ---: | --- |
| L0_llm_single | memory_heavy | 16 | 0.50 | 2.00 | test_failure |
| L0_llm_single | context_heavy | 10 | 0.50 | 2.00 | test_failure |
| L0_llm_single | skill_heavy | 10 | 0.50 | 2.00 | test_failure |
| L0_llm_single | traceback_repair | 5 | 0.40 | 2.00 | test_failure |
| L0_llm_single | multi_file_api | 4 | 0.25 | 2.00 | test_failure |
| L0_llm_single | repo_convention | 3 | 0.67 | 2.00 | success |
| L2_llm_multi | memory_heavy | 16 | 0.75 | 6.38 | success |
| L2_llm_multi | context_heavy | 10 | 0.70 | 6.50 | success |
| L2_llm_multi | skill_heavy | 10 | 0.60 | 6.40 | success |
| L2_llm_multi | traceback_repair | 5 | 0.80 | 6.80 | success |
| L2_llm_multi | multi_file_api | 4 | 0.50 | 7.00 | test_failure |
| L2_llm_multi | repo_convention | 3 | 0.67 | 5.67 | success |
| L5_llm_full | memory_heavy | 16 | 0.94 | 6.56 | success |
| L5_llm_full | context_heavy | 10 | 0.90 | 6.70 | success |
| L5_llm_full | skill_heavy | 10 | 0.80 | 7.00 | success |
| L5_llm_full | traceback_repair | 5 | 0.40 | 5.80 | test_failure |
| L5_llm_full | multi_file_api | 4 | 0.25 | 6.00 | test_failure |
| L5_llm_full | repo_convention | 3 | 1.00 | 6.33 | success |
