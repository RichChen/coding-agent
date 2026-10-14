# LLM Mechanism Ablation Summary

Run ID: `20260704_092308`
Generated at: `2026-07-04T12:35:27.389365+00:00`
Task count: `48`
Repeats: `2`
Seed: `42`
Mock LLM: `False`

| Config | success_rate+/-std | avg_steps+/-std | llm_calls | parse_err | patch_applied |
| --- | ---: | ---: | ---: | ---: | ---: |
| L0_llm_single | 0.46+/-0.02 | 2.00+/-0.00 | 99 | 3 | 78 |
| L0_llm_single failure taxonomy | `{'test_failure': 52, 'success': 44}` |  |  |  |  |
| L2_llm_multi | 0.71+/-0.02 | 6.28+/-0.01 | 153 | 10 | 116 |
| L2_llm_multi failure taxonomy | `{'test_failure': 28, 'success': 68}` |  |  |  |  |
| L5_llm_full | 0.80+/-0.05 | 6.32+/-0.22 | 147 | 10 | 124 |
| L5_llm_full failure taxonomy | `{'success': 77, 'test_failure': 19}` |  |  |  |  |

## Skill / Memory Injection

| Config | skill_cand | skill_inj | skill_gated | mem_cand | mem_inj |
| --- | ---: | ---: | ---: | ---: | ---: |
| L0_llm_single | 0 | 0 | 0 | 0 | 0 |
| L2_llm_multi | 0 | 0 | 0 | 0 | 0 |
| L5_llm_full | 522 | 13 | 509 | 1139 | 157 |

## Augmentation Policy Suppression

| Config | skill_suppressed | mem_suppressed |
| --- | ---: | ---: |
| L0_llm_single | 0 | 0 |
| L2_llm_multi | 0 | 0 |
| L5_llm_full | 89 | 230 |

## Context Expansion / JSON Repair

| Config | ctx_expand | paths_added | ctx_recovered | repair_try | repair_ok |
| --- | ---: | ---: | ---: | ---: | ---: |
| L0_llm_single | 0 | 0 | 0 | 0 | 0 |
| L2_llm_multi | 19 | 57 | 9 | 10 | 10 |
| L5_llm_full | 13 | 39 | 7 | 7 | 7 |

## By Task Category

| Config | Category | Tasks | Success Rate | Avg Steps | Main Failure |
| --- | --- | ---: | ---: | ---: | --- |
| L0_llm_single | memory_heavy | 32 | 0.50 | 2.00 | test_failure |
| L0_llm_single | context_heavy | 20 | 0.60 | 2.00 | success |
| L0_llm_single | skill_heavy | 20 | 0.35 | 2.00 | test_failure |
| L0_llm_single | traceback_repair | 10 | 0.40 | 2.00 | test_failure |
| L0_llm_single | multi_file_api | 8 | 0.12 | 2.00 | test_failure |
| L0_llm_single | repo_convention | 6 | 0.67 | 2.00 | success |
| L2_llm_multi | memory_heavy | 32 | 0.72 | 6.09 | success |
| L2_llm_multi | context_heavy | 20 | 0.85 | 6.15 | success |
| L2_llm_multi | skill_heavy | 20 | 0.65 | 6.50 | success |
| L2_llm_multi | traceback_repair | 10 | 0.70 | 6.70 | success |
| L2_llm_multi | multi_file_api | 8 | 0.38 | 6.50 | test_failure |
| L2_llm_multi | repo_convention | 6 | 0.83 | 6.00 | success |
| L5_llm_full | memory_heavy | 32 | 0.84 | 6.56 | success |
| L5_llm_full | context_heavy | 20 | 0.85 | 6.00 | success |
| L5_llm_full | skill_heavy | 20 | 0.80 | 5.90 | success |
| L5_llm_full | traceback_repair | 10 | 0.70 | 6.80 | success |
| L5_llm_full | multi_file_api | 8 | 0.50 | 6.62 | test_failure |
| L5_llm_full | repo_convention | 6 | 1.00 | 6.33 | success |
