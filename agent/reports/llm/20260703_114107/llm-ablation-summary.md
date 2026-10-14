# LLM Mechanism Ablation Summary

Run ID: `20260703_114107`
Generated at: `2026-07-03T12:07:10.089615+00:00`
Task count: `6`
Repeats: `1`
Seed: `42`
Mock LLM: `False`

| Config | success_rate+/-std | avg_steps+/-std | llm_calls | parse_err | patch_applied |
| --- | ---: | ---: | ---: | ---: | ---: |
| L0_llm_single | 0.33+/-0.00 | 2.00+/-0.00 | 6 | 0 | 8 |
| L0_llm_single failure taxonomy | `{'success': 2, 'test_failure': 4}` |  |  |  |  |
| L2_llm_multi | 0.83+/-0.00 | 7.50+/-0.00 | 10 | 0 | 14 |
| L2_llm_multi failure taxonomy | `{'success': 5, 'test_failure': 1}` |  |  |  |  |
| L3_llm_skill | 0.50+/-0.00 | 7.00+/-0.00 | 12 | 1 | 8 |
| L3_llm_skill failure taxonomy | `{'test_failure': 3, 'success': 3}` |  |  |  |  |
| L4_llm_memory | 0.33+/-0.00 | 6.83+/-0.00 | 11 | 0 | 7 |
| L4_llm_memory failure taxonomy | `{'test_failure': 4, 'success': 2}` |  |  |  |  |
| L5_llm_full | 0.67+/-0.00 | 7.50+/-0.00 | 11 | 0 | 10 |
| L5_llm_full failure taxonomy | `{'test_failure': 2, 'success': 4}` |  |  |  |  |

## Skill / Memory Injection

| Config | skill_cand | skill_inj | skill_gated | mem_cand | mem_inj |
| --- | ---: | ---: | ---: | ---: | ---: |
| L0_llm_single | 0 | 0 | 0 | 0 | 0 |
| L2_llm_multi | 0 | 0 | 0 | 0 | 0 |
| L3_llm_skill | 39 | 16 | 23 | 0 | 0 |
| L4_llm_memory | 0 | 0 | 0 | 35 | 18 |
| L5_llm_full | 39 | 7 | 32 | 39 | 8 |

## Augmentation Policy Suppression

| Config | skill_suppressed | mem_suppressed |
| --- | ---: | ---: |
| L0_llm_single | 0 | 0 |
| L2_llm_multi | 0 | 0 |
| L3_llm_skill | 0 | 0 |
| L4_llm_memory | 0 | 0 |
| L5_llm_full | 9 | 10 |

## Context Expansion / JSON Repair

| Config | ctx_expand | paths_added | ctx_recovered | repair_try | repair_ok |
| --- | ---: | ---: | ---: | ---: | ---: |
| L0_llm_single | 0 | 0 | 0 | 0 | 0 |
| L2_llm_multi | 0 | 0 | 0 | 0 | 0 |
| L3_llm_skill | 2 | 6 | 1 | 1 | 1 |
| L4_llm_memory | 2 | 6 | 0 | 0 | 0 |
| L5_llm_full | 2 | 6 | 1 | 0 | 0 |

## By Task Category

| Config | Category | Tasks | Success Rate | Avg Steps | Main Failure |
| --- | --- | ---: | ---: | ---: | --- |
| L0_llm_single | memory_heavy | 2 | 0.50 | 2.00 | success |
| L0_llm_single | skill_heavy | 2 | 0.00 | 2.00 | test_failure |
| L0_llm_single | context_heavy | 2 | 0.50 | 2.00 | success |
| L2_llm_multi | memory_heavy | 2 | 0.50 | 8.50 | success |
| L2_llm_multi | skill_heavy | 2 | 1.00 | 7.00 | success |
| L2_llm_multi | context_heavy | 2 | 1.00 | 7.00 | success |
| L3_llm_skill | memory_heavy | 2 | 0.00 | 6.50 | test_failure |
| L3_llm_skill | skill_heavy | 2 | 0.50 | 7.50 | test_failure |
| L3_llm_skill | context_heavy | 2 | 1.00 | 7.00 | success |
| L4_llm_memory | memory_heavy | 2 | 0.00 | 7.00 | test_failure |
| L4_llm_memory | skill_heavy | 2 | 0.00 | 6.50 | test_failure |
| L4_llm_memory | context_heavy | 2 | 1.00 | 7.00 | success |
| L5_llm_full | memory_heavy | 2 | 0.00 | 7.00 | test_failure |
| L5_llm_full | skill_heavy | 2 | 1.00 | 8.50 | success |
| L5_llm_full | context_heavy | 2 | 1.00 | 7.00 | success |
