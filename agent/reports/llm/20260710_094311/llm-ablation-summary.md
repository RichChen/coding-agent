# LLM Mechanism Ablation Summary

Run ID: `20260710_094311`
Generated at: `2026-07-10T09:43:18.114578+00:00`
Task count: `1`
Repeats: `1`
Seed: `42`
Mock LLM: `True`

| Config | success_rate+/-std | avg_steps+/-std | llm_calls | parse_err | patch_applied |
| --- | ---: | ---: | ---: | ---: | ---: |
| L0_llm_single | 1.00+/-0.00 | 2.00+/-0.00 | 1 | 0 | 1 |
| L0_llm_single failure taxonomy | `{'success': 1}` |  |  |  |  |
| L1_llm_planner | 1.00+/-0.00 | 5.00+/-0.00 | 1 | 0 | 1 |
| L1_llm_planner failure taxonomy | `{'success': 1}` |  |  |  |  |
| L2_llm_multi | 1.00+/-0.00 | 5.00+/-0.00 | 1 | 0 | 1 |
| L2_llm_multi failure taxonomy | `{'success': 1}` |  |  |  |  |
| L3_llm_skill | 1.00+/-0.00 | 5.00+/-0.00 | 1 | 0 | 1 |
| L3_llm_skill failure taxonomy | `{'success': 1}` |  |  |  |  |
| L4_llm_memory | 1.00+/-0.00 | 5.00+/-0.00 | 1 | 0 | 1 |
| L4_llm_memory failure taxonomy | `{'success': 1}` |  |  |  |  |
| L5_llm_full | 1.00+/-0.00 | 5.00+/-0.00 | 1 | 0 | 1 |
| L5_llm_full failure taxonomy | `{'success': 1}` |  |  |  |  |

## Skill / Memory Injection

| Config | skill_cand | skill_inj | skill_gated | mem_cand | mem_inj |
| --- | ---: | ---: | ---: | ---: | ---: |
| L0_llm_single | 0 | 0 | 0 | 0 | 0 |
| L1_llm_planner | 0 | 0 | 0 | 0 | 0 |
| L2_llm_multi | 0 | 0 | 0 | 0 | 0 |
| L3_llm_skill | 5 | 1 | 4 | 0 | 0 |
| L4_llm_memory | 0 | 0 | 0 | 1 | 1 |
| L5_llm_full | 5 | 0 | 5 | 1 | 0 |

## Augmentation Policy Suppression

| Config | skill_suppressed | mem_suppressed |
| --- | ---: | ---: |
| L0_llm_single | 0 | 0 |
| L1_llm_planner | 0 | 0 |
| L2_llm_multi | 0 | 0 |
| L3_llm_skill | 0 | 0 |
| L4_llm_memory | 0 | 0 |
| L5_llm_full | 1 | 1 |

## Context Expansion / JSON Repair

| Config | ctx_expand | paths_added | ctx_recovered | repair_try | repair_ok |
| --- | ---: | ---: | ---: | ---: | ---: |
| L0_llm_single | 0 | 0 | 0 | 0 | 0 |
| L1_llm_planner | 0 | 0 | 0 | 0 | 0 |
| L2_llm_multi | 0 | 0 | 0 | 0 | 0 |
| L3_llm_skill | 0 | 0 | 0 | 0 | 0 |
| L4_llm_memory | 0 | 0 | 0 | 0 | 0 |
| L5_llm_full | 0 | 0 | 0 | 0 | 0 |

## By Task Category

| Config | Category | Tasks | Success Rate | Avg Steps | Main Failure |
| --- | --- | ---: | ---: | ---: | --- |
| L0_llm_single | rename | 1 | 1.00 | 2.00 | success |
| L1_llm_planner | rename | 1 | 1.00 | 5.00 | success |
| L2_llm_multi | rename | 1 | 1.00 | 5.00 | success |
| L3_llm_skill | rename | 1 | 1.00 | 5.00 | success |
| L4_llm_memory | rename | 1 | 1.00 | 5.00 | success |
| L5_llm_full | rename | 1 | 1.00 | 5.00 | success |
