# H4 offline mechanism evidence

All four policies consume the same raw transcript. No model calls.
Overflow means a request was rejected before sending, not a failed provider request.

| Policy | Status | Applied | Summary calls (fixture) | Plugin requested / injected |
| --- | --- | --- | --- | --- |
| none | context_overflow | none | 0 | 0 / 0 |
| masking | context_overflow | masking | 0 | 0 / 0 |
| summary | ready | summary | 1 | 3 / 1 |
| mask-then-summary | ready | mask-then-summary | 1 | 3 / 1 |
