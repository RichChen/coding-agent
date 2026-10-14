# A5 complete image source continuation (v2)

2026-09-21. User instruction: solve large-repository transport/snapshot limits
and continue until coding-agent can build its memory pool. This supersedes the
size rejection boundary in A5-HOST-PREFLIGHT-24-CONTRACT.md for new attempts
only. Attempts 12–19 retain their original interpretation and hashes. Attempts
20/20b were parser failures; 20c and 21 only prepared source contexts, not runtime
images, environments, baseline/grader receipts, or memory-build eligibility.

Hypothesis: an immutable image containing the complete public upstream tree,
plus bounded candidate deltas, can preserve source completeness without raising
the live 8 MiB/2048-path transfer envelope. All 20 target identities and four
initial history identities remain fixed by the canonical handoff. Remaining
16 source environments follow the initial24 gate. No model calls, reservations,
paid memory builds, or pilot runs occur in this continuation.

The source manifest must bind archive SHA256/bytes, commit, all file contents,
file modes, symlink targets and directories. A new typed tree hash is explicitly
versioned; it does not replace or reinterpret the older regular-file tree hash.
Reject unsafe archive paths, duplicate members, special files, hard links,
escaping links and archive members under a link. Retain safe upstream symlinks.
Verify the extracted tree inside the image and again in the live workspace.
Private benchmark patches never enter a public source image.

The live runtime must retain the existing no-host-mount, read-only image,
unprivileged user, no network, bounded tmpfs/resources and verified cleanup
profile. It copies the complete immutable image base within the container.
Candidate export must check every source path and reject unassigned edits,
symlink/mode manipulation, changed base identity, excess delta bytes or paths.
Source, candidate and delta identities must agree after roundtrip reconstruction.
No omitted docs/tests/assets or generated files disguised as upstream files.

Success: exact complete source/image/live-workspace equality and bounded delta
roundtrip/rejection receipts, followed separately by each repository's own
dependency, full collection, baseline and known-good/negative grader evidence.
Failure: archive/tree mismatch, unsafe member, invalid image isolation, limit,
timeout, failed cleanup, missing exact benchmark identity, unreproduced defect,
or failed calibration. Record the failing gate; do not change test sets or
success criteria to obtain a pass. Full pytest/Django/SymPy/scikit-learn/Sphinx
collection requirements from v1 remain unchanged.

Preserve new attempt directories, exact script/contract/config hashes, commands,
logs, full per-task source and environment identities and failure/retry records.
Transport readiness is separate from grader readiness. Retain the earlier four
ready receipts only for their exact source/environment; subset evidence cannot
unlock the other memory sources. Shared gates (verified model/current CNY price,
independent build/pilot ledgers, stable dual fingerprints, B0–B3 receipt wiring)
remain required. This continuation produces eligibility, never launches build.
