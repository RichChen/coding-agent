# R2 detailed offline audit

All 44 assigned runs retained. Repeats are not independent tasks; trace and repair outcomes are not pooled.

| Phase / task | Strategy | Completed | Exact facts | All-correct / grader pass | Overflow | Null facts | Wrong nonnull | Summary calls | Main / summary tokens | Peak cache-aware USD | Mean elapsed s |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| trace / old-facts | mask-then-summary | 3/3 | 0/12 | 0/3 | 0 | 12 | 0 | 0 | 1431 / 0 | 0.00036247 | 2.112 |
| trace / old-facts | summary | 3/3 | 4/12 | 1/3 | 0 | 8 | 0 | 3 | 1765 / 13554 | 0.00316252 | 3.976 |
| trace / old-facts | none | 3/3 | 0/12 | 0/3 | 3 | 0 | 0 | 0 | 0 / 0 | 0.00000000 | 0.812 |
| trace / old-facts | masking | 3/3 | 0/12 | 0/3 | 0 | 12 | 0 | 0 | 1443 / 0 | 0.00030161 | 2.046 |
| trace / assistant-pressure | mask-then-summary | 3/3 | 0/12 | 0/3 | 0 | 12 | 0 | 3 | 1534 / 17654 | 0.00317002 | 3.856 |
| trace / assistant-pressure | none | 3/3 | 0/12 | 0/3 | 3 | 0 | 0 | 0 | 0 / 0 | 0.00000000 | 0.675 |
| trace / assistant-pressure | masking | 3/3 | 0/12 | 0/3 | 3 | 0 | 0 | 0 | 0 / 0 | 0.00000000 | 0.701 |
| trace / assistant-pressure | summary | 3/3 | 0/12 | 0/3 | 0 | 12 | 0 | 3 | 1568 / 17687 | 0.00163927 | 4.141 |
| trace / short-control | masking | 3/3 | 12/12 | 3/3 | 0 | 0 | 0 | 0 | 792 / 0 | 0.00033480 | 1.734 |
| trace / short-control | mask-then-summary | 3/3 | 12/12 | 3/3 | 0 | 0 | 0 | 0 | 792 / 0 | 0.00033480 | 1.890 |
| trace / short-control | summary | 3/3 | 12/12 | 3/3 | 0 | 0 | 0 | 0 | 792 / 0 | 0.00033480 | 2.031 |
| trace / short-control | none | 3/3 | 12/12 | 3/3 | 0 | 0 | 0 | 0 | 792 / 0 | 0.00033480 | 2.108 |
| repair / boltons-475-strutils-slice | summary | 2/2 | - | 0/2 | 2 | 0 | 0 | 0 | 2948 / 0 | 0.00068971 | 4.038 |
| repair / boltons-475-strutils-slice | masking | 2/2 | - | 0/2 | 2 | 0 | 0 | 0 | 2948 / 0 | 0.00035102 | 3.597 |
| repair / public-settings-001 | summary | 2/2 | - | 2/2 | 0 | 0 | 0 | 2 | 22158 / 2831 | 0.00409291 | 14.567 |
| repair / public-settings-001 | masking | 2/2 | - | 2/2 | 2 | 0 | 0 | 0 | 20560 / 0 | 0.00237947 | 12.666 |

Per-run input bytes, estimated input tokens, main/summary elapsed time and usage, cleanup, grades, and terminations: detailed-audit.json.
All cached/time-of-day costs are estimates, not account billing. Provider usage is kept separate from byte-based admission estimates.
All sources, prepared views, terminal replay, SQLite/JSONL, calls and token ledgers checked offline. No model/tool execution during audit.
The original frozen runner remains unchanged. This auditor parses JSONL by LF so literal Unicode line separators remain inside JSON strings.
