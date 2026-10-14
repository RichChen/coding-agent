# LLM Mechanism Ablation Summary

Run ID: `20260703_170314`
Generated at: `2026-07-03T17:27:07.085318+00:00`
Task count: `12`
Repeats: `1`
Seed: `42`
Mock LLM: `False`

| Config | success_rate+/-std | avg_steps+/-std | llm_calls | parse_err | patch_applied |
| --- | ---: | ---: | ---: | ---: | ---: |
| L0_llm_single | 0.42+/-0.00 | 2.00+/-0.00 | 14 | 2 | 16 |
| L0_llm_single failure taxonomy | `{'test_failure': 7, 'success': 5}` |  |  |  |  |
| L2_llm_multi | 0.92+/-0.00 | 7.00+/-0.00 | 20 | 1 | 22 |
| L2_llm_multi failure taxonomy | `{'success': 11, 'test_failure': 1}` |  |  |  |  |
| L5_llm_full | 0.75+/-0.00 | 6.58+/-0.00 | 19 | 1 | 21 |
| L5_llm_full failure taxonomy | `{'success': 9, 'test_failure': 3}` |  |  |  |  |

## Skill / Memory Injection

| Config | skill_cand | skill_inj | skill_gated | mem_cand | mem_inj |
| --- | ---: | ---: | ---: | ---: | ---: |
| L0_llm_single | 0 | 0 | 0 | 0 | 0 |
| L2_llm_multi | 0 | 0 | 0 | 0 | 0 |
| L5_llm_full | 62 | 9 | 53 | 80 | 29 |

## Augmentation Policy Suppression

| Config | skill_suppressed | mem_suppressed |
| --- | ---: | ---: |
| L0_llm_single | 0 | 0 |
| L2_llm_multi | 0 | 0 |
| L5_llm_full | 13 | 17 |

## Context Expansion / JSON Repair

| Config | ctx_expand | paths_added | ctx_recovered | repair_try | repair_ok |
| --- | ---: | ---: | ---: | ---: | ---: |
| L0_llm_single | 0 | 0 | 0 | 0 | 0 |
| L2_llm_multi | 2 | 6 | 2 | 1 | 1 |
| L5_llm_full | 1 | 3 | 1 | 1 | 1 |

## By Task Category

| Config | Category | Tasks | Success Rate | Avg Steps | Main Failure |
| --- | --- | ---: | ---: | ---: | --- |
| L0_llm_single | context_heavy | 4 | 0.50 | 2.00 | test_failure |
| L0_llm_single | skill_heavy | 4 | 0.25 | 2.00 | test_failure |
| L0_llm_single | memory_heavy | 4 | 0.50 | 2.00 | test_failure |
| L2_llm_multi | context_heavy | 4 | 1.00 | 7.00 | success |
| L2_llm_multi | skill_heavy | 4 | 1.00 | 7.75 | success |
| L2_llm_multi | memory_heavy | 4 | 0.75 | 6.25 | success |
| L5_llm_full | context_heavy | 4 | 1.00 | 6.00 | success |
| L5_llm_full | skill_heavy | 4 | 0.50 | 7.25 | success |
| L5_llm_full | memory_heavy | 4 | 0.75 | 6.50 | success |
