# A5 harness preflight 08

This run uses the pending model-price binding, the explicit 24-task
environment inventory, and the pending dual-source fingerprint. It is still
offline-only and fail-closed.

The blocked errors are the expected handoff blockers: unverified/provenance-
missing price data, zero baseline receipt rows, and an unfrozen dual
fingerprint. The denominator remains 20 targets plus four history tasks;
`model_calls` is zero and no paid build or pilot was started.
