# LLM Mechanism Ablation Summary

Protocol: `diagnostic_oracle` (legacy; not realistic repair evaluation)
Memory useful/stale counts are outcome proxies, not validity or adoption evidence.

Run ID: `20260919_024514`
Generated at: `2026-09-19T02:45:21.507027+00:00`
Task count: `1`
Repeats: `1`
Seed: `42`
Mock LLM: `True`

| Config | success_rate+/-std | avg_steps+/-std | llm_calls | parse_err | patch_applied |
| --- | ---: | ---: | ---: | ---: | ---: |
| L0_llm_single | 0.00+/-0.00 | 2.00+/-0.00 | 1 | 0 | 1 |
| L0_llm_single failure taxonomy | `{'test_failure': 1}` |  |  |  |  |
| L1_llm_planner | 0.00+/-0.00 | 8.00+/-0.00 | 2 | 0 | 2 |
| L1_llm_planner failure taxonomy | `{'test_failure': 1}` |  |  |  |  |
| L2_llm_multi | 0.00+/-0.00 | 8.00+/-0.00 | 2 | 0 | 2 |
| L2_llm_multi failure taxonomy | `{'test_failure': 1}` |  |  |  |  |
| L3_llm_skill | 0.00+/-0.00 | 8.00+/-0.00 | 2 | 0 | 2 |
| L3_llm_skill failure taxonomy | `{'test_failure': 1}` |  |  |  |  |
| L4_llm_memory | 0.00+/-0.00 | 8.00+/-0.00 | 2 | 0 | 2 |
| L4_llm_memory failure taxonomy | `{'test_failure': 1}` |  |  |  |  |
| L5_llm_full | 0.00+/-0.00 | 8.00+/-0.00 | 2 | 0 | 2 |
| L5_llm_full failure taxonomy | `{'test_failure': 1}` |  |  |  |  |

## Skill / Memory Injection

| Config | skill_cand | skill_inj | skill_gated | mem_cand | mem_inj |
| --- | ---: | ---: | ---: | ---: | ---: |
| L0_llm_single | 0 | 0 | 0 | 0 | 0 |
| L1_llm_planner | 0 | 0 | 0 | 0 | 0 |
| L2_llm_multi | 0 | 0 | 0 | 0 | 0 |
| L3_llm_skill | 10 | 2 | 8 | 0 | 0 |
| L4_llm_memory | 0 | 0 | 0 | 2 | 2 |
| L5_llm_full | 10 | 0 | 10 | 2 | 0 |

## Augmentation Policy Suppression

| Config | skill_suppressed | mem_suppressed |
| --- | ---: | ---: |
| L0_llm_single | 0 | 0 |
| L1_llm_planner | 0 | 0 |
| L2_llm_multi | 0 | 0 |
| L3_llm_skill | 0 | 0 |
| L4_llm_memory | 0 | 0 |
| L5_llm_full | 2 | 2 |

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
| L0_llm_single | rename | 1 | 0.00 | 2.00 | test_failure |
| L1_llm_planner | rename | 1 | 0.00 | 8.00 | test_failure |
| L2_llm_multi | rename | 1 | 0.00 | 8.00 | test_failure |
| L3_llm_skill | rename | 1 | 0.00 | 8.00 | test_failure |
| L4_llm_memory | rename | 1 | 0.00 | 8.00 | test_failure |
| L5_llm_full | rename | 1 | 0.00 | 8.00 | test_failure |
