# coding-agent

**English** · [中文](README.zh-CN.md)

A coding agent evaluation harness with strict answer isolation, plus two preregistered memory experiments run on it.

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

## What runs without an API key

The unit tests and the offline demo need no Docker, no SWE-bench image and no key:

```bash
cd agent && pip install -e ".[dev]"
python -m pytest -q
python -m reposkill_agent upgrade-demo --output reports/upgrade/my-demo

cd ../harness && pip install -e ".[dev]"
python -m pytest -q          # the LLM is always mocked
```

The demo writes a public workspace, a memory.db with per-record status and provenance, a manifest and report.md. When a dependency or API signature changes, the old record is rejected; unrelated file changes keep it valid; missing evidence yields unknown. Every injection receipt comes from a fixture host, so it claims no real-model gain.

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
