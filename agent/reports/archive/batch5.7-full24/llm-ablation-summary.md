# LLM Mechanism Ablation Summary

Run ID: `20260704_000519`
Generated at: `2026-07-04T00:40:21.974312+00:00`
Task count: `24`
Repeats: `1`
Seed: `42`
Mock LLM: `False`

| Config | success_rate+/-std | avg_steps+/-std | llm_calls | parse_err | patch_applied |
| --- | ---: | ---: | ---: | ---: | ---: |
| L3_llm_skill | 0.75+/-0.00 | 6.58+/-0.00 | 41 | 5 | 29 |
| L3_llm_skill failure taxonomy | `{'success': 18, 'test_failure': 6}` |  |  |  |  |
| L4_llm_memory | 0.83+/-0.00 | 6.83+/-0.00 | 40 | 2 | 37 |
| L4_llm_memory failure taxonomy | `{'success': 20, 'test_failure': 4}` |  |  |  |  |

## Skill / Memory Injection

| Config | skill_cand | skill_inj | skill_gated | mem_cand | mem_inj |
| --- | ---: | ---: | ---: | ---: | ---: |
| L3_llm_skill | 139 | 30 | 109 | 0 | 0 |
| L4_llm_memory | 0 | 0 | 0 | 238 | 105 |

## Augmentation Policy Suppression

| Config | skill_suppressed | mem_suppressed |
| --- | ---: | ---: |
| L3_llm_skill | 0 | 0 |
| L4_llm_memory | 0 | 0 |

## Context Expansion / JSON Repair

| Config | ctx_expand | paths_added | ctx_recovered | repair_try | repair_ok |
| --- | ---: | ---: | ---: | ---: | ---: |
| L3_llm_skill | 5 | 15 | 3 | 3 | 3 |
| L4_llm_memory | 5 | 15 | 4 | 2 | 2 |

## By Task Category

| Config | Category | Tasks | Success Rate | Avg Steps | Main Failure |
| --- | --- | ---: | ---: | ---: | --- |
| L3_llm_skill | repo_convention | 2 | 1.00 | 8.50 | success |
| L3_llm_skill | context_heavy | 5 | 1.00 | 5.80 | success |
| L3_llm_skill | multi_file_api | 2 | 0.00 | 7.50 | test_failure |
| L3_llm_skill | skill_heavy | 5 | 0.60 | 6.60 | success |
| L3_llm_skill | memory_heavy | 7 | 0.86 | 6.86 | success |
| L3_llm_skill | traceback_repair | 3 | 0.67 | 5.33 | success |
| L4_llm_memory | repo_convention | 2 | 1.00 | 7.00 | success |
| L4_llm_memory | context_heavy | 5 | 0.80 | 6.40 | success |
| L4_llm_memory | multi_file_api | 2 | 0.50 | 7.50 | success |
| L4_llm_memory | skill_heavy | 5 | 0.80 | 7.20 | success |
| L4_llm_memory | memory_heavy | 7 | 0.86 | 6.29 | success |
| L4_llm_memory | traceback_repair | 3 | 1.00 | 7.67 | success |
