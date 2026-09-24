# LLM Mechanism Ablation Summary

Run ID: `20260703_095044`
Generated at: `2026-07-03T09:51:16.419051+00:00`
Task count: `6`
Repeats: `1`
Seed: `42`
Mock LLM: `True`

| Config | success_rate+/-std | avg_steps+/-std | llm_calls | parse_err | patch_applied |
| --- | ---: | ---: | ---: | ---: | ---: |
| L0_llm_single | 0.00+/-0.00 | 2.00+/-0.00 | 6 | 0 | 0 |
| L0_llm_single failure taxonomy | `{'test_failure': 6}` |  |  |  |  |
| L2_llm_multi | 0.00+/-0.00 | 6.00+/-0.00 | 12 | 0 | 0 |
| L2_llm_multi failure taxonomy | `{'test_failure': 6}` |  |  |  |  |
| L3_llm_skill | 0.00+/-0.00 | 6.00+/-0.00 | 12 | 0 | 0 |
| L3_llm_skill failure taxonomy | `{'test_failure': 6}` |  |  |  |  |
| L4_llm_memory | 0.00+/-0.00 | 6.00+/-0.00 | 12 | 0 | 0 |
| L4_llm_memory failure taxonomy | `{'test_failure': 6}` |  |  |  |  |
| L5_llm_full | 0.00+/-0.00 | 6.00+/-0.00 | 12 | 0 | 0 |
| L5_llm_full failure taxonomy | `{'test_failure': 6}` |  |  |  |  |

## Skill / Memory Injection

| Config | skill_cand | skill_inj | skill_gated | mem_cand | mem_inj |
| --- | ---: | ---: | ---: | ---: | ---: |
| L0_llm_single | 0 | 0 | 0 | 0 | 0 |
| L2_llm_multi | 0 | 0 | 0 | 0 | 0 |
| L3_llm_skill | 44 | 18 | 26 | 0 | 0 |
| L4_llm_memory | 0 | 0 | 0 | 20 | 14 |
| L5_llm_full | 44 | 18 | 26 | 20 | 14 |

## Context Expansion / JSON Repair

| Config | ctx_expand | paths_added | ctx_recovered | repair_try | repair_ok |
| --- | ---: | ---: | ---: | ---: | ---: |
| L0_llm_single | 0 | 0 | 0 | 0 | 0 |
| L2_llm_multi | 0 | 0 | 0 | 0 | 0 |
| L3_llm_skill | 0 | 0 | 0 | 0 | 0 |
| L4_llm_memory | 0 | 0 | 0 | 0 | 0 |
| L5_llm_full | 0 | 0 | 0 | 0 | 0 |

## By Task Category

| Config | Category | Tasks | Success Rate | Avg Steps | Main Failure |
| --- | --- | ---: | ---: | ---: | --- |
| L0_llm_single | memory_heavy | 2 | 0.00 | 2.00 | test_failure |
| L0_llm_single | skill_heavy | 2 | 0.00 | 2.00 | test_failure |
| L0_llm_single | context_heavy | 2 | 0.00 | 2.00 | test_failure |
| L2_llm_multi | memory_heavy | 2 | 0.00 | 6.00 | test_failure |
| L2_llm_multi | skill_heavy | 2 | 0.00 | 6.00 | test_failure |
| L2_llm_multi | context_heavy | 2 | 0.00 | 6.00 | test_failure |
| L3_llm_skill | memory_heavy | 2 | 0.00 | 6.00 | test_failure |
| L3_llm_skill | skill_heavy | 2 | 0.00 | 6.00 | test_failure |
| L3_llm_skill | context_heavy | 2 | 0.00 | 6.00 | test_failure |
| L4_llm_memory | memory_heavy | 2 | 0.00 | 6.00 | test_failure |
| L4_llm_memory | skill_heavy | 2 | 0.00 | 6.00 | test_failure |
| L4_llm_memory | context_heavy | 2 | 0.00 | 6.00 | test_failure |
| L5_llm_full | memory_heavy | 2 | 0.00 | 6.00 | test_failure |
| L5_llm_full | skill_heavy | 2 | 0.00 | 6.00 | test_failure |
| L5_llm_full | context_heavy | 2 | 0.00 | 6.00 | test_failure |
