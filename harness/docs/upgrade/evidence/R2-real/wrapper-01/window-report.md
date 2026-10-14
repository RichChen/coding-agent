# Corrected window feasibility

No model calls or Docker execution. Original snapshots verified; policy checks cannot mutate raw.
Supersedes window-preflight.json. That first preflight inadvertently used an in-place masking helper on its raw list; saved window-inputs were written before mutation and remain authoritative. Paid wrapper inputs and results are unaffected.

| Source run | Window | First batch required | Eligible batches | First batch fits | Any observed raw pressure | Decision |
|---|---:|---:|---:|---|---|---|
| repair-boltons-475-strutils-slice-r1-masking | 12000 | 13224 | 0 | False | True | skip_paid |
| repair-boltons-475-strutils-slice-r1-masking | 16000 | 13224 | 0 | True | False | no_observed_summary_pressure |
| repair-boltons-475-strutils-slice-r1-masking | 24000 | 13224 | 0 | True | False | no_observed_summary_pressure |
| repair-boltons-475-strutils-slice-r1-summary | 12000 | 13224 | 0 | False | True | skip_paid |
| repair-boltons-475-strutils-slice-r1-summary | 16000 | 13224 | 0 | True | False | no_observed_summary_pressure |
| repair-boltons-475-strutils-slice-r1-summary | 24000 | 13224 | 0 | True | False | no_observed_summary_pressure |
| repair-boltons-475-strutils-slice-r2-masking | 12000 | 13224 | 0 | False | True | skip_paid |
| repair-boltons-475-strutils-slice-r2-masking | 16000 | 13224 | 0 | True | False | no_observed_summary_pressure |
| repair-boltons-475-strutils-slice-r2-masking | 24000 | 13224 | 0 | True | False | no_observed_summary_pressure |
| repair-boltons-475-strutils-slice-r2-summary | 12000 | 13224 | 0 | False | True | skip_paid |
| repair-boltons-475-strutils-slice-r2-summary | 16000 | 13224 | 0 | True | False | no_observed_summary_pressure |
| repair-boltons-475-strutils-slice-r2-summary | 24000 | 13224 | 0 | True | False | no_observed_summary_pressure |
| repair-public-settings-001-r1-masking | 12000 | 8724 | 0 | True | True | observed_pressure_requires_new_repair_contract |
| repair-public-settings-001-r1-masking | 16000 | 8724 | 0 | True | False | no_observed_summary_pressure |
| repair-public-settings-001-r1-masking | 24000 | 8724 | 0 | True | False | no_observed_summary_pressure |
| repair-public-settings-001-r1-summary | 12000 | 8733 | 0 | True | True | observed_pressure_requires_new_repair_contract |
| repair-public-settings-001-r1-summary | 16000 | 8733 | 0 | True | False | no_observed_summary_pressure |
| repair-public-settings-001-r1-summary | 24000 | 8733 | 0 | True | False | no_observed_summary_pressure |
| repair-public-settings-001-r2-masking | 12000 | 8723 | 0 | True | True | observed_pressure_requires_new_repair_contract |
| repair-public-settings-001-r2-masking | 16000 | 8723 | 0 | True | False | no_observed_summary_pressure |
| repair-public-settings-001-r2-masking | 24000 | 8723 | 0 | True | False | no_observed_summary_pressure |
| repair-public-settings-001-r2-summary | 12000 | 8723 | 0 | True | True | observed_pressure_requires_new_repair_contract |
| repair-public-settings-001-r2-summary | 16000 | 8723 | 0 | True | False | no_observed_summary_pressure |
| repair-public-settings-001-r2-summary | 24000 | 8723 | 0 | True | False | no_observed_summary_pressure |

Required window is conservative byte-based admission plus 2048 output reservation, not provider tokenizer usage.
Each snapshot is checked independently; fixture fit does not prove LLM summary fit, and a larger window does not predict the next trajectory.
