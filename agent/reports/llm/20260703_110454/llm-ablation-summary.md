# LLM Mechanism Ablation Summary

Run ID: `20260703_110454`
Generated at: `2026-07-03T11:29:53.838356+00:00`
Task count: `6`
Repeats: `1`
Seed: `42`
Mock LLM: `False`

| Config | success_rate+/-std | avg_steps+/-std | llm_calls | parse_err | patch_applied |
| --- | ---: | ---: | ---: | ---: | ---: |
| L0_llm_single | 0.17+/-0.00 | 2.00+/-0.00 | 8 | 2 | 2 |
| L0_llm_single failure taxonomy | `{'test_failure': 5, 'success': 1}` |  |  |  |  |
| L2_llm_multi | 0.17+/-0.00 | 6.33+/-0.00 | 15 | 5 | 6 |
| L2_llm_multi failure taxonomy | `{'test_failure': 5, 'success': 1}` |  |  |  |  |
| L3_llm_skill | 0.50+/-0.00 | 6.50+/-0.00 | 12 | 4 | 9 |
| L3_llm_skill failure taxonomy | `{'test_failure': 3, 'success': 3}` |  |  |  |  |
| L4_llm_memory | 0.50+/-0.00 | 7.00+/-0.00 | 14 | 5 | 8 |
| L4_llm_memory failure taxonomy | `{'test_failure': 3, 'success': 3}` |  |  |  |  |
| L5_llm_full | 0.17+/-0.00 | 6.50+/-0.00 | 15 | 6 | 6 |
| L5_llm_full failure taxonomy | `{'test_failure': 5, 'success': 1}` |  |  |  |  |

## Skill / Memory Injection

| Config | skill_cand | skill_inj | skill_gated | mem_cand | mem_inj |
| --- | ---: | ---: | ---: | ---: | ---: |
| L0_llm_single | 0 | 0 | 0 | 0 | 0 |
| L2_llm_multi | 0 | 0 | 0 | 0 | 0 |
| L3_llm_skill | 35 | 15 | 20 | 0 | 0 |
| L4_llm_memory | 0 | 0 | 0 | 25 | 14 |
| L5_llm_full | 39 | 11 | 28 | 9 | 5 |

## Context Expansion / JSON Repair

| Config | ctx_expand | paths_added | ctx_recovered | repair_try | repair_ok |
| --- | ---: | ---: | ---: | ---: | ---: |
| L0_llm_single | 0 | 0 | 0 | 0 | 0 |
| L2_llm_multi | 3 | 9 | 1 | 4 | 4 |
| L3_llm_skill | 1 | 3 | 0 | 2 | 2 |
| L4_llm_memory | 1 | 3 | 0 | 3 | 3 |
| L5_llm_full | 3 | 9 | 1 | 4 | 4 |

## By Task Category

| Config | Category | Tasks | Success Rate | Avg Steps | Main Failure |
| --- | --- | ---: | ---: | ---: | --- |
| L0_llm_single | memory_heavy | 2 | 0.00 | 2.00 | test_failure |
| L0_llm_single | skill_heavy | 2 | 0.00 | 2.00 | test_failure |
| L0_llm_single | context_heavy | 2 | 0.50 | 2.00 | success |
| L2_llm_multi | memory_heavy | 2 | 0.00 | 6.50 | test_failure |
| L2_llm_multi | skill_heavy | 2 | 0.00 | 6.00 | test_failure |
| L2_llm_multi | context_heavy | 2 | 0.50 | 6.50 | success |
| L3_llm_skill | memory_heavy | 2 | 0.00 | 6.50 | test_failure |
| L3_llm_skill | skill_heavy | 2 | 0.50 | 6.00 | success |
| L3_llm_skill | context_heavy | 2 | 1.00 | 7.00 | success |
| L4_llm_memory | memory_heavy | 2 | 0.00 | 6.00 | test_failure |
| L4_llm_memory | skill_heavy | 2 | 0.50 | 8.00 | success |
| L4_llm_memory | context_heavy | 2 | 1.00 | 7.00 | success |
| L5_llm_full | memory_heavy | 2 | 0.00 | 6.50 | test_failure |
| L5_llm_full | skill_heavy | 2 | 0.00 | 6.50 | test_failure |
| L5_llm_full | context_heavy | 2 | 0.50 | 6.50 | success |
