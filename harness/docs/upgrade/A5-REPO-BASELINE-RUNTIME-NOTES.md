# A5 repository baseline runtime notes

The image-backed continuation keeps all 24 canonical identities and the complete
archives. These are environment/runner corrections, not benchmark changes.
No model calls, memory builds, ledger reservations or paid pilots are launched.

Retained smoke attempts 25g–25l exposed a masked `/workspace`, wrong archive
selection, missing test patch in the gold tree, and incompatible Sphinx packages.
Their preliminary `baseline_ready` flags are not final calibration evidence.
Attempt 26 was stopped in host staging after a regression detected Git CRLF
conversion. Attempt 27 disables that conversion and compares full typed trees
instead of building full Git indexes.

Baseline is complete source plus the exact private test patch. Known-good is
that same baseline plus the exact private gold patch. Each image contains its
own `/opt/repo`; startup copies it within the container into the bounded writable
workspace. Dependencies and generated compiled extensions are image artifacts,
not substituted upstream source. Runtime keeps the existing unprivileged,
read-only-root, no-network, no-host-mount profile and cleanup checks.

Django uses its own `tests/runtests.py` with SQLite and serial execution.
Collection uses the checkout's discovery without executing the tests or creating
databases. Test results are structured unittest callbacks, including subtests;
discovery errors and setup failures cannot establish a reproduced defect.
Test-body exceptions (such as a defect-induced TypeError) are failures, while
exceptions from setup/teardown are environment errors. Observer v2 uses the
unittest traceback phase to distinguish them and records its own source hash.
Other repositories use full pytest collection and exact selected F2P execution.
Sphinx dependencies are version-specific. No Flask image is used.

All expected F2P identities must execute and fail at baseline, and pass with the
gold patch. Unexpected baseline passes remain explicit mismatches; never drop
them, change private identities or downgrade the all-F2P criterion to any-F2P.
Full collection is separately required. This stage alone does not establish
independent grader calibration, P2P preservation or memory-build eligibility.

Further retained diagnostics: Django docstring labels bind by exact AST docstring
and collected runtime identity; SymPy short labels bind uniquely within all
patched test files. Sphinx-8721 requires the entire test file because its prior
HTML builder populates shared fixture state consumed by the EPUB test. Its
Pygments profile must match the older source's HTML assertions. SymPy 1.6's own
testing-helper tests import its native `Failed` class, so the observer initializes
the native helper before pytest's conftest sets `_running_pytest`; no source or
test is changed or excluded. Each recipe change has a new attempt.

Attempt 30 caught umask normalization of upstream modes. Attempt 31 proves
`umask 000` preserves the complete archive in both private images; subsequent
runtime rechecks use that copy operation. Attempt 28's complete Django migration
module still reproduced only two of four declared F2P tests. That mismatch is
retained as a blocking result, not reclassified as green.

The configured learn-Codex reference path is absent on this host. The existing
repository grader and the locally available learn-claude-code s12 isolation
lesson are implementation references only; they do not supply task evidence.
