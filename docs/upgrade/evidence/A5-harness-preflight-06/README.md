# A5 harness preflight 06

This is an offline gate result. It does not build an image, pull an image,
read an API key, call a model, or start a paid pilot.

`readiness.json` is intentionally **blocked** because the current contract
still lacks:

- a verified model snapshot and current CNY price binding;
- 24 independently produced environment/baseline receipts (20 targets plus
  four historical pool tasks); and
- a frozen fingerprint from both the harness and coding-agent repositories.

The result retains the complete 20 + 4 denominator and records
`model_calls: 0`, `paid_build_started: false`, and `paid_pilot_started: false`.
The environment template names all 24 tasks but has no receipt rows, so it is
not evidence of a baseline run.
