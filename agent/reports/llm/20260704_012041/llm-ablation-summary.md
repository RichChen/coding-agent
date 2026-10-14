# LLM Mechanism Ablation Summary

Run ID: `20260704_012041`
Generated at: `2026-07-04T02:26:09.977785+00:00`
Task count: `24`
Repeats: `1`
Seed: `42`
Mock LLM: `False`

| Config | success_rate+/-std | avg_steps+/-std | llm_calls | parse_err | patch_applied |
| --- | ---: | ---: | ---: | ---: | ---: |
| L0_llm_single | 0.42+/-0.00 | 2.00+/-0.00 | 25 | 1 | 16 |
| L0_llm_single failure taxonomy | `{'success': 10, 'test_failure': 14}` |  |  |  |  |
| L2_llm_multi | 0.75+/-0.00 | 6.67+/-0.00 | 40 | 2 | 32 |
| L2_llm_multi failure taxonomy | `{'success': 18, 'test_failure': 6}` |  |  |  |  |
| L4_llm_memory | 0.67+/-0.00 | 6.38+/-0.00 | 40 | 3 | 24 |
| L4_llm_memory failure taxonomy | `{'success': 16, 'test_failure': 8}` |  |  |  |  |
| L5_llm_full | 0.79+/-0.00 | 6.21+/-0.00 | 37 | 2 | 29 |
| L5_llm_full failure taxonomy | `{'success': 19, 'test_failure': 5}` |  |  |  |  |

## Skill / Memory Injection

| Config | skill_cand | skill_inj | skill_gated | mem_cand | mem_inj |
| --- | ---: | ---: | ---: | ---: | ---: |
| L0_llm_single | 0 | 0 | 0 | 0 | 0 |
| L2_llm_multi | 0 | 0 | 0 | 0 | 0 |
| L4_llm_memory | 0 | 0 | 0 | 222 | 102 |
| L5_llm_full | 129 | 2 | 127 | 221 | 35 |

## Augmentation Policy Suppression

| Config | skill_suppressed | mem_suppressed |
| --- | ---: | ---: |
| L0_llm_single | 0 | 0 |
| L2_llm_multi | 0 | 0 |
| L4_llm_memory | 0 | 0 |
| L5_llm_full | 25 | 61 |

## Context Expansion / JSON Repair

| Config | ctx_expand | paths_added | ctx_recovered | repair_try | repair_ok |
| --- | ---: | ---: | ---: | ---: | ---: |
| L0_llm_single | 0 | 0 | 0 | 0 | 0 |
| L2_llm_multi | 7 | 21 | 5 | 2 | 2 |
| L4_llm_memory | 7 | 21 | 3 | 2 | 2 |
| L5_llm_full | 6 | 18 | 3 | 2 | 2 |

## By Task Category

| Config | Category | Tasks | Success Rate | Avg Steps | Main Failure |
| --- | --- | ---: | ---: | ---: | --- |
| L0_llm_single | repo_convention | 2 | 0.50 | 2.00 | success |
| L0_llm_single | context_heavy | 5 | 0.60 | 2.00 | success |
| L0_llm_single | multi_file_api | 2 | 0.00 | 2.00 | test_failure |
| L0_llm_single | skill_heavy | 5 | 0.40 | 2.00 | test_failure |
| L0_llm_single | memory_heavy | 7 | 0.29 | 2.00 | test_failure |
| L0_llm_single | traceback_repair | 3 | 0.67 | 2.00 | success |
| L2_llm_multi | repo_convention | 2 | 1.00 | 7.00 | success |
| L2_llm_multi | context_heavy | 5 | 0.80 | 6.00 | success |
| L2_llm_multi | multi_file_api | 2 | 0.50 | 7.50 | success |
| L2_llm_multi | skill_heavy | 5 | 0.80 | 6.60 | success |
| L2_llm_multi | memory_heavy | 7 | 0.71 | 7.29 | success |
| L2_llm_multi | traceback_repair | 3 | 0.67 | 5.67 | success |
| L4_llm_memory | repo_convention | 2 | 1.00 | 7.00 | success |
| L4_llm_memory | context_heavy | 5 | 0.60 | 6.00 | success |
| L4_llm_memory | multi_file_api | 2 | 0.50 | 7.50 | success |
| L4_llm_memory | skill_heavy | 5 | 0.60 | 6.80 | success |
| L4_llm_memory | memory_heavy | 7 | 0.71 | 6.29 | success |
| L4_llm_memory | traceback_repair | 3 | 0.67 | 5.33 | success |
| L5_llm_full | repo_convention | 2 | 0.50 | 6.00 | success |
| L5_llm_full | context_heavy | 5 | 1.00 | 5.80 | success |
| L5_llm_full | multi_file_api | 2 | 0.50 | 7.50 | success |
| L5_llm_full | skill_heavy | 5 | 0.80 | 6.40 | success |
| L5_llm_full | memory_heavy | 7 | 0.86 | 6.43 | success |
| L5_llm_full | traceback_repair | 3 | 0.67 | 5.33 | success |
