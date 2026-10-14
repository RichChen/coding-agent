# LLM Mechanism Ablation Summary

Run ID: `20260703_231744`
Generated at: `2026-07-04T00:04:56.055582+00:00`
Task count: `24`
Repeats: `1`
Seed: `42`
Mock LLM: `False`

| Config | success_rate+/-std | avg_steps+/-std | llm_calls | parse_err | patch_applied |
| --- | ---: | ---: | ---: | ---: | ---: |
| L0_llm_single | 0.46+/-0.00 | 2.00+/-0.00 | 24 | 0 | 19 |
| L0_llm_single failure taxonomy | `{'success': 11, 'test_failure': 13}` |  |  |  |  |
| L2_llm_multi | 0.71+/-0.00 | 6.83+/-0.00 | 44 | 4 | 29 |
| L2_llm_multi failure taxonomy | `{'success': 17, 'test_failure': 7}` |  |  |  |  |
| L5_llm_full | 0.79+/-0.00 | 6.42+/-0.00 | 38 | 3 | 31 |
| L5_llm_full failure taxonomy | `{'success': 19, 'test_failure': 5}` |  |  |  |  |

## Skill / Memory Injection

| Config | skill_cand | skill_inj | skill_gated | mem_cand | mem_inj |
| --- | ---: | ---: | ---: | ---: | ---: |
| L0_llm_single | 0 | 0 | 0 | 0 | 0 |
| L2_llm_multi | 0 | 0 | 0 | 0 | 0 |
| L5_llm_full | 136 | 12 | 124 | 231 | 36 |

## Augmentation Policy Suppression

| Config | skill_suppressed | mem_suppressed |
| --- | ---: | ---: |
| L0_llm_single | 0 | 0 |
| L2_llm_multi | 0 | 0 |
| L5_llm_full | 17 | 61 |

## Context Expansion / JSON Repair

| Config | ctx_expand | paths_added | ctx_recovered | repair_try | repair_ok |
| --- | ---: | ---: | ---: | ---: | ---: |
| L0_llm_single | 0 | 0 | 0 | 0 | 0 |
| L2_llm_multi | 7 | 21 | 6 | 4 | 4 |
| L5_llm_full | 3 | 9 | 2 | 2 | 2 |

## By Task Category

| Config | Category | Tasks | Success Rate | Avg Steps | Main Failure |
| --- | --- | ---: | ---: | ---: | --- |
| L0_llm_single | repo_convention | 2 | 0.50 | 2.00 | success |
| L0_llm_single | context_heavy | 5 | 0.80 | 2.00 | success |
| L0_llm_single | multi_file_api | 2 | 0.00 | 2.00 | test_failure |
| L0_llm_single | skill_heavy | 5 | 0.20 | 2.00 | test_failure |
| L0_llm_single | memory_heavy | 7 | 0.43 | 2.00 | test_failure |
| L0_llm_single | traceback_repair | 3 | 0.67 | 2.00 | success |
| L2_llm_multi | repo_convention | 2 | 0.50 | 6.00 | success |
| L2_llm_multi | context_heavy | 5 | 1.00 | 7.00 | success |
| L2_llm_multi | multi_file_api | 2 | 0.00 | 7.00 | test_failure |
| L2_llm_multi | skill_heavy | 5 | 0.60 | 7.20 | success |
| L2_llm_multi | memory_heavy | 7 | 0.86 | 7.14 | success |
| L2_llm_multi | traceback_repair | 3 | 0.67 | 5.67 | success |
| L5_llm_full | repo_convention | 2 | 0.50 | 6.00 | success |
| L5_llm_full | context_heavy | 5 | 0.80 | 6.00 | success |
| L5_llm_full | multi_file_api | 2 | 0.00 | 6.50 | test_failure |
| L5_llm_full | skill_heavy | 5 | 0.80 | 6.80 | success |
| L5_llm_full | memory_heavy | 7 | 1.00 | 6.57 | success |
| L5_llm_full | traceback_repair | 3 | 1.00 | 6.33 | success |
