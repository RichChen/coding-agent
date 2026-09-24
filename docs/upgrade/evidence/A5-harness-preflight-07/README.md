# A5 harness preflight 07

Offline-only preflight using `configs/a5/environment-preflight.template.json`.
The template explicitly lists all 20 target tasks and four historical pool
tasks, while keeping `rows` empty. Therefore this is denominator/coverage
evidence, not a claim that any repository baseline has run.

The gate is blocked and records zero model calls, no paid build, and no paid
pilot. A verified model/price binding, 24 independent environment and
baseline receipts, and both-side source fingerprints remain required.
