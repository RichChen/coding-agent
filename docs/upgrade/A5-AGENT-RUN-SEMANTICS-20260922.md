# A5 agent run semantics

This document freezes the agent-side meaning of the 240-task preparation before any provider, model, build, or pilot call.

## Variants

- **B0**: memory retrieval is disabled; candidate and injection sets are empty.
- **B1**: use lexical set overlap on the same frozen history; at most three candidates, two selected records, and 4096 bytes. Injection is raw public trajectory text.
- **B2**: the ranking and quotas are the same as B1; injection is the canonical `procedure_skill` structured projection.
- **B3**: B2 plus dependency validity against current `RepoFacts`; `invalid` and `unknown` dependencies are never injected.

The selector has zero external model calls. The H4 adapter emits public evidence proposals and memory candidates only. It does not execute actions, read private EvaluationSpec material, or call a second model budget.

## Evidence and receipts

An injection receipt must bind `operation_id` and `attempt_id`; its actual slice hash must equal `actual_hash`. A rejected receipt has no content range or actual hash. Missing token or cost provenance keeps usage `unknown`; failures, unknown outcomes, and interruptions retain their cost.

`observed_following` stays `unknown` unless an independent later action or verification proves following or non-following. A prepared view, a candidate list, or a model self-report cannot prove injection or following.

## Outcomes

`pass` requires a complete frozen grader collection, every required check passing, an evaluation reference, and cleanup. `fail` means a valid environment where required checks remain unfixed. `partial` cannot be promoted to pass. `invalid_env` covers source, image, collection, dependency, isolation, timeout, cleanup, or receipt failures. `not_run` remains in the denominator. `unknown` is never pass and keeps cost allocated.

## Run boundary

The current preparation is read-only: all 240 assignments are `planned_not_started`, provider/model seeds are null, and no pilot has started. Each target remains blocked until its own source tree, pinned environment, collection fingerprint, baseline receipt, private grader calibration, cleanup receipt, and source fingerprint are present. Evidence from one repository cannot satisfy another target.

## Memory import boundary

The import manifest targets about 15–25 future `validated_lightweight` records from coding-harness (20 is the planning midpoint), but currently contains zero records. External lightweight status is not internal `MemoryRecord.status=validated`; every record must be reconstructed and pass the agent validator. Missing public trajectory, independent validation, dependency mapping, usage provenance, hashes, cold-frozen status, or private exclusion causes rejection.
