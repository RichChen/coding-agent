# LLM Mechanism Ablation Summary

Run ID: `20260703_225809`
Generated at: `2026-07-03T23:13:56.499847+00:00`
Task count: `12`
Repeats: `1`
Seed: `42`
Mock LLM: `False`

| Config | success_rate+/-std | avg_steps+/-std | llm_calls | parse_err | patch_applied |
| --- | ---: | ---: | ---: | ---: | ---: |
| L3_llm_skill | 1.00+/-0.00 | 7.08+/-0.00 | 19 | 0 | 21 |
| L3_llm_skill failure taxonomy | `{'success': 12}` |  |  |  |  |
| L4_llm_memory | 0.83+/-0.00 | 6.42+/-0.00 | 20 | 3 | 18 |
| L4_llm_memory failure taxonomy | `{'test_failure': 2, 'success': 10}` |  |  |  |  |

## Skill / Memory Injection

| Config | skill_cand | skill_inj | skill_gated | mem_cand | mem_inj |
| --- | ---: | ---: | ---: | ---: | ---: |
| L3_llm_skill | 68 | 14 | 54 | 0 | 0 |
| L4_llm_memory | 0 | 0 | 0 | 74 | 42 |

## Augmentation Policy Suppression

| Config | skill_suppressed | mem_suppressed |
| --- | ---: | ---: |
| L3_llm_skill | 0 | 0 |
| L4_llm_memory | 0 | 0 |

## Context Expansion / JSON Repair

| Config | ctx_expand | paths_added | ctx_recovered | repair_try | repair_ok |
| --- | ---: | ---: | ---: | ---: | ---: |
| L3_llm_skill | 3 | 9 | 3 | 0 | 0 |
| L4_llm_memory | 2 | 6 | 3 | 2 | 2 |

## By Task Category

| Config | Category | Tasks | Success Rate | Avg Steps | Main Failure |
| --- | --- | ---: | ---: | ---: | --- |
| L3_llm_skill | context_heavy | 4 | 1.00 | 6.75 | success |
| L3_llm_skill | skill_heavy | 4 | 1.00 | 7.00 | success |
| L3_llm_skill | memory_heavy | 4 | 1.00 | 7.50 | success |
| L4_llm_memory | context_heavy | 4 | 0.75 | 6.25 | success |
| L4_llm_memory | skill_heavy | 4 | 1.00 | 7.50 | success |
| L4_llm_memory | memory_heavy | 4 | 0.75 | 5.50 | success |
