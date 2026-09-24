# R2 summary pilot results

Exploratory fixed-history and two-task repair pilot; not a benchmark success-rate claim.

| Phase | Task | Strategy | Completed / assigned | Exact facts | Independent pass | Summary calls | Provider tokens | Peak estimate USD |
|---|---|---|---:|---:|---:|---:|---:|---:|
| trace | old-facts | none | 3/3 | 0/12 | 0/3 | 0 | 0 | 0 |
| trace | old-facts | masking | 3/3 | 0/12 | 0/3 | 0 | 1443 | 0.000301608 |
| trace | old-facts | summary | 3/3 | 4/12 | 1/3 | 3 | 15319 | 0.0031625159999999998 |
| trace | old-facts | mask-then-summary | 3/3 | 0/12 | 0/3 | 0 | 1431 | 0.00036247199999999997 |
| trace | assistant-pressure | none | 3/3 | 0/12 | 0/3 | 0 | 0 | 0 |
| trace | assistant-pressure | masking | 3/3 | 0/12 | 0/3 | 0 | 0 | 0 |
| trace | assistant-pressure | summary | 3/3 | 0/12 | 0/3 | 3 | 19255 | 0.0016392720000000002 |
| trace | assistant-pressure | mask-then-summary | 3/3 | 0/12 | 0/3 | 3 | 19188 | 0.003170016 |
| trace | short-control | none | 3/3 | 12/12 | 3/3 | 0 | 792 | 0.00033479999999999995 |
| trace | short-control | masking | 3/3 | 12/12 | 3/3 | 0 | 792 | 0.00033479999999999995 |
| trace | short-control | summary | 3/3 | 12/12 | 3/3 | 0 | 792 | 0.00033479999999999995 |
| trace | short-control | mask-then-summary | 3/3 | 12/12 | 3/3 | 0 | 792 | 0.00033479999999999995 |
| repair | boltons-475-strutils-slice | masking | 2/2 | - | 0/2 | 0 | 2948 | 0.000351024 |
| repair | boltons-475-strutils-slice | summary | 2/2 | - | 0/2 | 0 | 2948 | 0.0006897120000000001 |
| repair | public-settings-001 | masking | 2/2 | - | 2/2 | 0 | 20560 | 0.002379468 |
| repair | public-settings-001 | summary | 2/2 | - | 2/2 | 2 | 24989 | 0.004092912 |

All assigned runs retained, including overflow and invalid environment. No automatic paid retry.
Unknown usage/cost is retained in results.json; 0-call rejected requests cost zero.
Fixed-history exact facts and repair grader pass are different outcomes; do not pool them.
Cache/time-of-day affect billed estimates. Both cache-aware intervals and conservative run commitments are retained.
Literal summary value presence is not a semantic-faithfulness guarantee.
