# A5 initial 24 host preflight — execution contract

2026-09-21. Supersedes only the earlier read-only execution boundary. Canonical
handoff d18d9fa78da00230c30d62c61abce168b91812871d3435e14702aad7a761774c and
consumption manifest 33ab6922caf6909888d672a8d97df49f305ed4cdabb8c402dfca4bca88cb0180
fix the 20 targets and four exact historical candidates. The denominator is 24.

Question: can each full pinned source reproduce its baseline defect and support
an independently calibrated repository grader inside a pinned isolated environment?
No model, provider, ledger reserve, memory build or pilot is permitted.

First acquire complete immutable upstream commit archives and inventory every
file/member. Preserve archive, content tree, member hashes, modes and provenance.
This stage explicitly rejects more than 8 MiB or 2048 files as invalid_env;
do not trim source or use image-backed transfer to bypass this instruction.
Keep the full rejected archive. Do not execute repository code on the Windows host.

Only sources within the envelope progress to repository-specific dependency/image
preparation and complete test collection, baseline execution, known-good calibration,
test/config tampering and fake-output negative rejection, and verified cleanup.
Record actual Python/pytest/package versions, image identity, collection IDs/hash,
baseline outcomes, private patch/spec hashes and all command logs. Pytest itself
requires a runner that imports the candidate pytest; importing an unrelated image
pytest is not acceptable calibration. Flask images/receipts prove no other repo.

Ready requires complete source, valid environment, nonempty unique full collection,
reproduced F2P failure, passing known-good with P2P preserved, negative rejection,
and cleanup. Dependency/collection errors, missing source, baseline unexpectedly
passing, grader unavailability, timeout and limits remain explicit non-ready rows.
No fabricated empty failures/counts or denominator reduction. Retain every attempt
in a new A5-harness-preflight directory, including failure/retry ledger and receipts.

Use pinned public base images with task-specific dependency evidence. Fetching
source/dependencies and building Docker images is authorized through normal tool
approvals. No paid model calls. The budget-scope conflict remains unresolved.
Only after initial24 passes may remaining16 receive their own preflight; neither
condition launches a build. Report initial24 results and blockers first.

Reference path C:/Users/23500/Desktop/src/learn-Codex-main is absent. The locally
available D:/crq/src/learn-claude-code-main/docs/zh/s12-worktree-task-isolation.md
was consulted for task-ID-bound isolated directories and retained lifecycle state;
existing full-repo grader is the implementation reference, not reusable Flask evidence.

## Environment refinements after retained attempts

Attempt 13 retained five image-build failures: Docker's builder tried to resolve
the local dependency-image digest against Docker Hub. Attempt 14 starts each task
image directly from the pinned official Python 3.7.17 digest and reuses identical
dependency layers. It retains each exact public source and its own image identity.

The public issue for pytest-9359 explicitly requires Python 3.9 and says 3.7 does
not reproduce the issue. Attempt 14's baseline-pass result is therefore retained;
a targeted retry will use Python 3.9.19 digest
`6e4a4eb8ce1238cb552dd44cc37f9187e448e9bfcf24262c5badfd69fee1bef0`.
The runner will retain pytest's built-in cacheprovider (its own suite tests the
cache fixture), with cache storage redirected to `/tmp/a5-cache`. Disabling it in
attempt 14 caused an unrelated fixture-missing error. No task/test IDs, success
criteria, private patches or source files are changed by these environment fixes.

Historical pytest-5103 (pytest 4.5) reproduced the target defect in attempt 14,
but known-good retained 12 unrelated failures in attrs rendering and plugin
discovery. A separate historical dependency profile pins attrs 18.2.0 (the old
Attribute.cmp interface), pluggy 0.9.0 (the pkg_resources entry-point interface
mocked by this source's own tests), and hypothesis 4.14.5 (compatible with attrs
18.2.0). The modern profile remains unchanged. Its retry keeps Python 3.7.17,
the complete collection and both source patches unchanged; it is not a waiver
for those 12 failures and does not infer readiness from the newer pytest tasks.

The historical dependency retry's baseline no longer showed ten of the twelve
unrelated failures. Its two remaining plugin-discovery tests explicitly require
automatic entry-point loading, which the general runner had disabled. A further
historical-only retry restores the upstream default inside the fixed image,
verifies that Hypothesis is the only loaded plugin distribution, and records the
setting and versions. Source/tests/expected IDs remain unchanged. No external
plugins, host mounts or network are made available to the test container.

The final audited result is in
`docs/upgrade/evidence/A5-harness-preflight-19-final-audit/`: 24/24 source
snapshots, 5 complete collections, 4 ready rows, 1 grader-unavailable row and
19 invalid_env rows. The audit checked 15,921 file/receipt conditions, retained
all retries, and found no owned Docker containers left behind. This is a measured
host-preflight result, not paid-build authorization; remaining16 memory-source
preflights are still not started.
