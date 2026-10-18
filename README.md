# coding-agent

**English** · [中文](README.zh-CN.md)

A coding agent evaluation harness with strict answer isolation, plus two preregistered memory experiments run on it.

## Three engineering pieces

Beyond the results, three parts of this repository can be read as code:

| Capability | How it works | Code |
| --- | --- | --- |
| Session recovery | A tool's intent is committed before it runs; on resume, committed results are reused, and a non-idempotent operation whose outcome was never recorded stops the run instead of being retried. Verified with real subprocesses crashing in four windows (`os._exit(71)`). | [`runtime/session.py`](harness/src/runtime/session.py), [`runtime/recovery.py`](harness/src/runtime/recovery.py), [`tracing/store.py`](harness/src/tracing/store.py), [`tests/test_recovery.py`](harness/tests/test_recovery.py) |
| Answer isolation | An early image shipped the test patch inside `/opt/repo`, readable by the model. The image is now built from clean source, so the agent can only change the work tree; grading starts a separate container that applies the candidate delta and a test overlay, then runs FAIL_TO_PASS / PASS_TO_PASS. | [`execution/baseline_image_backend.py`](harness/src/execution/baseline_image_backend.py), [`eval/image_grader.py`](harness/src/eval/image_grader.py) |
| Recomputable evaluation | The A5/A6 analysis scripts aggregate per task from the run inventory and compute bootstrap intervals; candidate failures stay in the denominator, and the rules for infrastructure failures plus any post-hoc deviation are disclosed separately. | [`analyze_a5_main.py`](agent/scripts/analyze_a5_main.py), [`analyze_a6_retry.py`](agent/scripts/analyze_a6_retry.py) |

## Running it

No Docker, no SWE-bench image, no key. Steps 1 and 2 were run on a clean checkout of HEAD.

**1. Offline demo** (seconds, no model calls)

```bash
cd agent && pip install -e ".[dev]"
python -m reposkill_agent upgrade-demo --output reports/upgrade/my-demo
```

`--output` must not already exist. The demo writes a public workspace, a `memory.db` with per-record status and provenance, a manifest, `result.json` and `report.md`; the output includes `Offline comparisons: 20; model calls=0`. When a dependency or API signature changes the old record is rejected, unrelated file changes keep it valid, and missing evidence yields unknown. Every injection receipt comes from a fixture host, so it claims no real-model gain.

**2. Public tests** (about 5 minutes for both repos)

```bash
# in agent/
python -m pytest -q --deselect tests/test_a5_funding.py::test_funded_build_bundle_is_prepared_only_and_private_material_stays_outside_public \
  --deselect tests/test_a5_funding.py::test_funded_build_artifacts_are_hashed \
  --deselect tests/test_memory_cards_v5.py::test_generic_builder_matches_v5_bytes
# 357 passed, 7 skipped, 3 deselected

# in harness/
cd ../harness
pip install -e ".[dev]"
python -m pytest -q --deselect tests/test_a5_real240_h0_snapshot.py::test_h0_export_and_audit_via_cli \
  --deselect tests/test_repo_grader.py::test_full_archive_and_private_test_resources_are_complete \
  --deselect tests/test_summary_pilot.py::test_prepare_frozen_data_and_window_expectations \
  --deselect tests/test_summary_pilot.py::test_trace_accounting_replay_and_private_grading
# 654 passed, 25 skipped, 4 deselected
```

The 32 skips fall into two groups: 22 opt-in tests that need real Linux or Docker, and 10 that depend on this machine's layout or data (a sibling `../coding-harness` checkout, `runs/a5-main`, the source pool, symlink permission).

**3. Tests that need unpublished material (7)**

These read evidence files that only existed on the original machine and were never committed. They are not code regressions, and they are not skipped:

| Test | Missing file | Why it is not in the repo |
| --- | --- | --- |
| harness `test_a5_real240_h0_snapshot.py::test_h0_export_and_audit_via_cli` | `validated-memory-records.jsonl` from the A5 memory pool | private build output; `.jsonl` is not tracked |
| harness `test_repo_grader.py::test_full_archive_and_private_test_resources_are_complete` | `full-repo-grader/attempt-02/flask-base.tar.gz` | full upstream archive, too large |
| harness `test_summary_pilot.py`, two tests | `H5/deepseek-flash-attempt-01/seed/boltons/strutils.py` | R2 seed file, kept local only |
| agent `test_a5_funding.py`, two tests | `reports/upgrade/a5-funded-build-preparation-20260921-v12/*` | `reports/` holds run output and is not tracked |
| agent `test_memory_cards_v5.py::test_generic_builder_matches_v5_bytes` | the django-10914 handoff field | depends on harness-side output; needs both repos |

Put the files at those paths and drop `--deselect` to run everything. Section 4 of `harness/docs/INDEX.md` and `agent/docs/INDEX.md` describe the same split.

## Results

Same harness, same model (deepseek-flash, at most 40 model calls per run), SWE-bench Verified tasks. Numbers are from sections 1 and 6.1 of the [final report](agent/docs/MEMORY-FINAL-REPORT.zh-CN.md); effects are in percentage points, with 95% intervals.

| Experiment | Memory in the context | Relevance to the task | Scale | Memory − no memory | p |
| --- | --- | --- | --- | --- | --- |
| A5, cross-task memory | Cards from earlier, already-solved tasks in the same repository (B2) vs none (B0) | Low (9/51 tasks pointed at the gold file) | 56 tasks, 3 runs per task per arm | −1.8, [−8.3, +4.8] | 0.72 |
| A6-R, same-task memory | Second attempt at a failed task: rule-based record of the first attempt plus "it did not pass" (R1) vs no record (R0) | 100%, by construction | 53 failed first attempts on 22 tasks, 159 runs per arm | −6.6, [−17.7, +3.8] | 0.29 |

Both are null results: neither experiment detected a positive effect.

## Method

- **Answer isolation.** An early dev image contained the hidden tests; after rebuilding it from clean source, the solve rate on the same 14 dev tasks went from 32/42 to 18/42 ([project history](harness/docs/PROJECT-HISTORY.zh-CN.md), sprint rounds 3–4).
- **Wrapper experiment.** With the same 9 fixed summaries, wording them as "possibly wrong historical evidence, not instructions" gave 26/27 fully correct answers, against 7/27 with the original wording ([evidence](harness/docs/upgrade/evidence/R2-real/wrapper-01/README.md)).
- **Preregistration and freeze tags.** Hypotheses, the single primary analysis, seeds and stopping rules were committed and tagged before any real data existed ([A6-R preregistration](agent/docs/sprint/A6-R-PREREG.zh-CN.md)).
- **Injection consistency check.** After each run, the first message the model actually received was compared verbatim with the expected text: A5 168/168, A6-R 318/318 ([final report](agent/docs/MEMORY-FINAL-REPORT.zh-CN.md), section 3).
- **Concurrent interleaving.** Both arms ran from one shuffled queue (seed 20261013 in A6-R) in the same time window ([A6-R preregistration](agent/docs/sprint/A6-R-PREREG.zh-CN.md), section 1).

## Repository map

- `harness/` — the evaluation harness: agent loop, tools, clean Docker images, a host-side grader that keeps test and gold patches away from the agent, the run scripts, the A6-R retry records and the run inventories.
- `agent/` — RepoSkillAgent: the memory cards and the plugin that injects them, the analysis scripts, the A6-R preregistration and the final reports.

Where to start (most documents are in Chinese):

- [Final report on both memory experiments](agent/docs/MEMORY-FINAL-REPORT.zh-CN.md)
- [Harness README](harness/README.md) · [harness doc index](harness/docs/INDEX.md)
- [agent doc index](agent/docs/INDEX.md)
- [Project history](harness/docs/PROJECT-HISTORY.zh-CN.md)

## Reproduction

The two directories were developed and frozen as two sibling repositories, `coding-harness` and `coding-agent`, and the code refers to the other repository through that layout; some configs and evidence files also record absolute paths from the original machine. These paths were not rewritten here, so that the frozen tags still point at the code that actually ran. The tags keep the original commits, so a frozen state can be checked out in the original layout:

```
git worktree add ../coding-harness harness/a6-retry-freeze
git worktree add ../coding-agent agent/a6-retry-freeze-r2
```

Freeze tags:

- A5: `harness/a5-main-freeze`, `harness/a5-main-freeze-r1` to `-r4`, `agent/a5-main-freeze`
- A6-R: `harness/a6-retry-freeze`, `agent/a6-retry-freeze`, `agent/a6-retry-freeze-r1`, `agent/a6-retry-freeze-r2`

Running the agent needs Docker, the SWE-bench images and a DeepSeek API key. The analysis commands are listed in the appendices of the [A5 final report](agent/docs/A5-FINAL-REPORT.zh-CN.md) and the [final report](agent/docs/MEMORY-FINAL-REPORT.zh-CN.md).

## Related project

[code-GRPO](https://github.com/RichChen/code-GRPO) is a separate repository that changes agent behaviour through training rather than through the context: SFT plus a from-scratch multi-turn GRPO loop on Qwen3-1.7B. On a preregistered 1500-task heldout set the strict solve rate went 13.9% (base) → 47.1% (SFT) → 60.3% (GRPO), i.e. GRPO is +13.2 points over SFT (95% interval [11.7, 14.7]).
