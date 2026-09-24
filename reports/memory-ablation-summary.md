# Memory Ablation Summary

Generated at: 2026-07-02T08:52:02.984953+00:00

## Variants

- A: `use_memory=false` (no memory)
- B: `use_memory=true` (with memory)

## Aggregate Metrics

| Metric | No Memory | With Memory |
| --- | ---: | ---: |
| success_rate | 1.00 | 1.00 |
| avg_steps | 5.00 | 5.00 |
| avg_wall_time_ms | 775.80 | 754.37 |
| avg_replan_count | 0.00 | 0.00 |
| skill_validated_total | 4 | 4 |
| skill_negative_transfer_total | 0 | 0 |
| memory_retrieval_total | 0 | 43 |
| memory_useful_total | 0 | 3 |
| memory_stale_or_wrong_total | 0 | 0 |
