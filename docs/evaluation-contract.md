# Evaluation Contract (Phase 6)

## Goal

Use ablations to measure mechanism value, not just demo pass rate.

## Evaluation Layers

Three layers must be kept separate:

1. **Fake plumbing eval** (`phase6_tiny_24`): runner/trace/report stability only.
2. **Deterministic mechanism eval** (`phase6_hard_12`, A0-A5): explainable planner/skill/memory chain without LLM.
3. **Real LLM mechanism eval** (`phase6_hard_12`, L0-L5): DeepSeek/OpenAI-compatible patch generation evidence.

Deterministic eval cannot replace LLM eval. LLM eval is final project evidence for model-driven patching. Fake/deterministic eval remains for CI and mechanism regression.

## Current Toy Limits

- `phase6_tiny_24` is still low-difficulty and mostly deterministic.
- It is useful for plumbing validation, but weak for mechanism gain claims.
- Mechanism conclusions should primarily rely on `phase6_hard_12` and seeded-memory runs.

- Mechanism conclusions for skill/memory should primarily rely on `phase6_hard_12` deterministic runs.
- LLM conclusions must use `scripts/run_llm_ablation.py` (never commit API keys).

## Config Matrix (Deterministic A0-A5)

- `A0_baseline`: no planner, no multi-agent, no skill, no memory
- `A1_planner`: planner only
- `A2_multi_agent`: planner + role agents
- `A3_skill`: planner + role agents + skills
- `A4_memory`: planner + role agents + memory
- `A5_full`: planner + role agents + skills + memory

## Config Matrix (LLM L0-L5)

- `L0_llm_single`: inspect + LLM patch + test (no planner graph)
- `L1_llm_planner`: planner single-graph + LLM developer
- `L2_llm_multi`: planner + role agents + LLM developer
- `L3_llm_skill`: L2 + skills
- `L4_llm_memory`: L2 + memory
- `L5_llm_full`: L2 + skills + memory

LLM reports store prompt **length summaries only**, never full prompts or API keys.

## Reproducibility

- Use fixed task sets:
  - plumbing: `benchmarks/tasks/phase6_tiny_24.yaml`
  - hard: `benchmarks/tasks/phase6_hard_12.yaml`
- Set seed via `--seed` (default `42`)
- Use repeats via `--repeats` (default `3`) for stability and std reporting
- Default memory isolation: each repeat uses independent memory directory
- Optional seeded memory mode: `--seed-memory` (shared memory across repeats)

## Metrics

- success rate
- avg steps
- avg wall time
- avg replan count
- skill negative transfer total
- memory useful total
- memory stale/wrong total
- failure taxonomy distribution
- per-repeat variance (std) for major metrics

## Commands

```bash
python scripts/run_phase6_ablation.py --tasks benchmarks/tasks/phase6_tiny_24.yaml --repeats 3 --seed 42
```

```bash
python scripts/run_phase6_ablation.py --tasks benchmarks/tasks/phase6_hard_12.yaml --repeats 3 --seed 42
```

```bash
python scripts/run_phase6_ablation.py --tasks benchmarks/tasks/phase6_hard_12.yaml --repeats 3 --seed-memory
```

```bash
# Offline mock LLM ablation (CI-safe)
python scripts/run_llm_ablation.py --tasks benchmarks/tasks/phase6_hard_12.yaml --limit 3 --mock-llm
```

```bash
# Real DeepSeek smoke (set env vars locally; never commit keys)
python scripts/run_llm_ablation.py --tasks benchmarks/tasks/phase6_hard_12.yaml --limit 3 --repeats 1 --seed 42
```
