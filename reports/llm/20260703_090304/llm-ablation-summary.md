# LLM Mechanism Ablation Summary

Run ID: `20260703_090304`
Generated at: `2026-07-03T09:03:10.204815+00:00`
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

## By Task Category

| Config | Category | Tasks | Success Rate | Avg Steps | Main Failure |
| --- | --- | ---: | ---: | ---: | --- |
| L0_llm_single | other | 3 | 0.00 | 2.00 | test_failure |
| L2_llm_multi | other | 3 | 0.00 | 6.00 | test_failure |
