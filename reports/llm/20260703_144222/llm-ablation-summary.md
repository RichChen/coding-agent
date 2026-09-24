# LLM Mechanism Ablation Summary

Run ID: `20260703_144222`
Generated at: `2026-07-03T15:09:12.137185+00:00`
Task count: `7`
Repeats: `1`
Seed: `42`
Mock LLM: `False`

| Config | success_rate+/-std | avg_steps+/-std | llm_calls | parse_err | patch_applied |
| --- | ---: | ---: | ---: | ---: | ---: |
| L4_llm_memory | 0.86+/-0.00 | 7.43+/-0.00 | 13 | 1 | 12 |
| L4_llm_memory failure taxonomy | `{'success': 6, 'test_failure': 1}` |  |  |  |  |
| L5_llm_full | 0.86+/-0.00 | 6.43+/-0.00 | 11 | 1 | 11 |
| L5_llm_full failure taxonomy | `{'success': 6, 'test_failure': 1}` |  |  |  |  |

## Skill / Memory Injection

| Config | skill_cand | skill_inj | skill_gated | mem_cand | mem_inj |
| --- | ---: | ---: | ---: | ---: | ---: |
| L4_llm_memory | 0 | 0 | 0 | 93 | 36 |
| L5_llm_full | 23 | 0 | 23 | 85 | 29 |

## Augmentation Policy Suppression

| Config | skill_suppressed | mem_suppressed |
| --- | ---: | ---: |
| L4_llm_memory | 0 | 0 |
| L5_llm_full | 4 | 1 |

## Context Expansion / JSON Repair

| Config | ctx_expand | paths_added | ctx_recovered | repair_try | repair_ok |
| --- | ---: | ---: | ---: | ---: | ---: |
| L4_llm_memory | 1 | 3 | 1 | 1 | 1 |
| L5_llm_full | 0 | 0 | 1 | 1 | 1 |

## By Task Category

| Config | Category | Tasks | Success Rate | Avg Steps | Main Failure |
| --- | --- | ---: | ---: | ---: | --- |
| L4_llm_memory | memory_heavy | 7 | 0.86 | 7.43 | success |
| L5_llm_full | memory_heavy | 7 | 0.86 | 6.43 | success |
