# Phase 6 Ablation Summary

Run ID: `20260702_090858`
Generated at: `2026-07-02T09:12:36.853781+00:00`
Task count: `24`
Repeats: `2`
Seed: `42`
Seed memory: `False`

| Config | success_rate±std | avg_steps±std | avg_replan±std | skill_neg_transfer | memory_useful | memory_stale |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A0_baseline | 1.00±0.00 | 2.00±0.00 | 0.00±0.00 | 0 | 0 | 0 |
| A0_baseline failure taxonomy | `{'success': 48}` |  |  |  |  |  |
| A1_planner | 1.00±0.00 | 5.00±0.00 | 0.00±0.00 | 0 | 0 | 0 |
| A1_planner failure taxonomy | `{'success': 48}` |  |  |  |  |  |
| A2_multi_agent | 1.00±0.00 | 5.00±0.00 | 0.00±0.00 | 0 | 0 | 0 |
| A2_multi_agent failure taxonomy | `{'success': 48}` |  |  |  |  |  |
| A3_skill | 1.00±0.00 | 5.00±0.00 | 0.00±0.00 | 0 | 0 | 0 |
| A3_skill failure taxonomy | `{'success': 48}` |  |  |  |  |  |
| A4_memory | 1.00±0.00 | 5.00±0.00 | 0.00±0.00 | 0 | 46 | 0 |
| A4_memory failure taxonomy | `{'success': 48}` |  |  |  |  |  |
| A5_full | 1.00±0.00 | 5.00±0.00 | 0.00±0.00 | 0 | 46 | 0 |
| A5_full failure taxonomy | `{'success': 48}` |  |  |  |  |  |
