# LLM Mechanism Ablation Summary

Run ID: `20260703_092209`
Generated at: `2026-07-03T09:22:24.944610+00:00`
Task count: `3`
Repeats: `1`
Seed: `42`
Mock LLM: `True`

| Config | success_rate+/-std | avg_steps+/-std | llm_calls | parse_err | patch_applied |
| --- | ---: | ---: | ---: | ---: | ---: |
| L0_llm_single | 0.00+/-0.00 | 2.00+/-0.00 | 3 | 0 | 0 |
| L0_llm_single failure taxonomy | `{'test_failure': 3}` |  |  |  |  |
| L2_llm_multi | 0.00+/-0.00 | 6.00+/-0.00 | 6 | 0 | 0 |
| L2_llm_multi failure taxonomy | `{'test_failure': 3}` |  |  |  |  |
| L3_llm_skill | 0.00+/-0.00 | 6.00+/-0.00 | 6 | 0 | 0 |
| L3_llm_skill failure taxonomy | `{'test_failure': 3}` |  |  |  |  |
| L4_llm_memory | 0.00+/-0.00 | 6.00+/-0.00 | 6 | 0 | 0 |
| L4_llm_memory failure taxonomy | `{'test_failure': 3}` |  |  |  |  |
| L5_llm_full | 0.00+/-0.00 | 6.00+/-0.00 | 6 | 0 | 0 |
| L5_llm_full failure taxonomy | `{'test_failure': 3}` |  |  |  |  |

## Skill / Memory Injection

| Config | skill_cand | skill_inj | skill_gated | mem_cand | mem_inj |
| --- | ---: | ---: | ---: | ---: | ---: |
| L0_llm_single | 0 | 0 | 0 | 0 | 0 |
| L2_llm_multi | 0 | 0 | 0 | 0 | 0 |
| L3_llm_skill | 6 | 0 | 6 | 0 | 0 |
| L4_llm_memory | 0 | 0 | 0 | 5 | 5 |
| L5_llm_full | 6 | 0 | 6 | 5 | 5 |

## By Task Category

| Config | Category | Tasks | Success Rate | Avg Steps | Main Failure |
| --- | --- | ---: | ---: | ---: | --- |
| L0_llm_single | other | 3 | 0.00 | 2.00 | test_failure |
| L2_llm_multi | other | 3 | 0.00 | 6.00 | test_failure |
| L3_llm_skill | other | 3 | 0.00 | 6.00 | test_failure |
| L4_llm_memory | other | 3 | 0.00 | 6.00 | test_failure |
| L5_llm_full | other | 3 | 0.00 | 6.00 | test_failure |
