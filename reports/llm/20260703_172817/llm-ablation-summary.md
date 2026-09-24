# LLM Mechanism Ablation Summary

Run ID: `20260703_172817`
Generated at: `2026-07-03T17:46:56.136741+00:00`
Task count: `12`
Repeats: `1`
Seed: `42`
Mock LLM: `False`

| Config | success_rate+/-std | avg_steps+/-std | llm_calls | parse_err | patch_applied |
| --- | ---: | ---: | ---: | ---: | ---: |
| L3_llm_skill | 0.83+/-0.00 | 6.75+/-0.00 | 19 | 0 | 17 |
| L3_llm_skill failure taxonomy | `{'success': 10, 'test_failure': 2}` |  |  |  |  |
| L4_llm_memory | 0.67+/-0.00 | 6.58+/-0.00 | 22 | 4 | 19 |
| L4_llm_memory failure taxonomy | `{'test_failure': 4, 'success': 8}` |  |  |  |  |

## Skill / Memory Injection

| Config | skill_cand | skill_inj | skill_gated | mem_cand | mem_inj |
| --- | ---: | ---: | ---: | ---: | ---: |
| L3_llm_skill | 66 | 23 | 43 | 0 | 0 |
| L4_llm_memory | 0 | 0 | 0 | 80 | 45 |

## Augmentation Policy Suppression

| Config | skill_suppressed | mem_suppressed |
| --- | ---: | ---: |
| L3_llm_skill | 0 | 0 |
| L4_llm_memory | 0 | 0 |

## Context Expansion / JSON Repair

| Config | ctx_expand | paths_added | ctx_recovered | repair_try | repair_ok |
| --- | ---: | ---: | ---: | ---: | ---: |
| L3_llm_skill | 3 | 9 | 3 | 0 | 0 |
| L4_llm_memory | 2 | 6 | 1 | 3 | 3 |

## By Task Category

| Config | Category | Tasks | Success Rate | Avg Steps | Main Failure |
| --- | --- | ---: | ---: | ---: | --- |
| L3_llm_skill | context_heavy | 4 | 1.00 | 7.00 | success |
| L3_llm_skill | skill_heavy | 4 | 0.75 | 7.25 | success |
| L3_llm_skill | memory_heavy | 4 | 0.75 | 6.00 | success |
| L4_llm_memory | context_heavy | 4 | 0.75 | 6.25 | success |
| L4_llm_memory | skill_heavy | 4 | 0.50 | 6.75 | success |
| L4_llm_memory | memory_heavy | 4 | 0.75 | 6.75 | success |
