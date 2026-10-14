# SWE-bench Contamination Probe Report

Generated: 2026-06-26T16:55:44.783329+00:00
Model: `deepseek-v4-pro` (temperature=0.0, max_tokens=2048, repeats=5)

> File-localization probe (no repo context), replicating *The SWE-Bench Illusion*. The model is **non-deterministic at temperature=0** (reasoning model), so each instance is sampled `repeats` times and scored by hit frequency.

## Aggregate

- Instances scored: **10** (skipped: 0); repeats per instance: **5**; valid attempts: 48, truncated: 2
- **Pooled exact rate**: 54.2% (26/48 attempts)
- **Per-instance exact-frequency mean**: 54.0%
- **Pooled basename-or-better**: 68.8%
- **Per-round exact swing**: 50%–60% (rounds: 50%, 56%, 60%, 50%, 56%)
- **Majority-exact instances**: 5/10 (exact is the modal answer over repeats)
- **Majority-localized instances** (≥basename): 7/10 (named the right file on a majority of samples)
- Total tokens: 52916 (prompt 21135, completion 31781)
- Est. cost: n/a (pass `--cost-per-1k` to estimate)

## Per-Instance Results

| instance_id | repo | gold | exact hits | basename | wrong | trunc | distinct predictions | baseline (REWORK) |
|-------------|------|------|-----------|----------|-------|-------|----------------------|-------------------|
| `swebench_sympy__sympy-24909` | sympy/sympy | `sympy/physics/units/prefixes.py` | **5/5** | 0 | 0 | 0 | `sympy/physics/units/prefixes.py`×5 | 0/5 |
| `swebench_pallets__flask-4992` | pallets/flask | `src/flask/config.py` | **0/5** | 5 | 0 | 0 | `flask/config.py`×5 | 5/5 |
| `swebench_sympy__sympy-24213` | sympy/sympy | `sympy/physics/units/unitsystem.py` | **5/5** | 0 | 0 | 0 | `sympy/physics/units/unitsystem.py`×5 | 5/5 |
| `swebench_sympy__sympy-24152` | sympy/sympy | `sympy/physics/quantum/tensorproduct.py` | **5/5** | 0 | 0 | 0 | `sympy/physics/quantum/tensorproduct.py`×5 | 3/5 |
| `swebench_sympy__sympy-24102` | sympy/sympy | `sympy/parsing/mathematica.py` | **2/5** | 1 | 2 | 0 | `sympy/parsing/mathematica.py`×2, `sympy/parsing/mathematica/mathematica_parser.py`×1, `sympy/parsing/mathematica/mathematica.py`×1, `sympy/parsing/lark/grammars/mathematica.lark`×1 | 0/5 |
| `swebench_sympy__sympy-24066` | sympy/sympy | `sympy/physics/units/unitsystem.py` | **4/4** | 0 | 0 | 1 | `sympy/physics/units/unitsystem.py`×4 | 3/5 |
| `swebench_sympy__sympy-23262` | sympy/sympy | `sympy/utilities/lambdify.py` | **0/5** | 0 | 5 | 0 | `sympy/printing/pycode.py`×5 | 0/5 |
| `swebench_sympy__sympy-23191` | sympy/sympy | `sympy/printing/pretty/pretty.py` | **0/4** | 1 | 3 | 1 | `sympy/vector/printing.py`×3, `sympy/vector/pretty.py`×1 | 0/5 |
| `swebench_sympy__sympy-23117` | sympy/sympy | `sympy/tensor/array/ndim_array.py` | **5/5** | 0 | 0 | 0 | `sympy/tensor/array/ndim_array.py`×5 | 0/5 |
| `swebench_psf__requests-3362` | psf/requests | `requests/utils.py` | **0/5** | 0 | 5 | 0 | `requests/models.py`×5 | 0/5 |

## Cross-Validation with REWORK Bimodal Pass Rates

Reference: `reports/report_20260626T101113.md` baseline pass matrix (5 runs).

| Pattern | instance | exact freq | loc freq (≥basename) | baseline passes |
|---------|----------|------------|----------------------|-----------------|
| never pass | `swebench_sympy__sympy-24909` | 5/5 | 5/5 | 0/5 |
| always pass | `swebench_pallets__flask-4992` | 0/5 | 5/5 | 5/5 |
| always pass | `swebench_sympy__sympy-24213` | 5/5 | 5/5 | 5/5 |
| mixed | `swebench_sympy__sympy-24152` | 5/5 | 5/5 | 3/5 |
| never pass | `swebench_sympy__sympy-24102` | 2/5 | 3/5 | 0/5 |
| mixed | `swebench_sympy__sympy-24066` | 4/4 | 4/4 | 3/5 |
| never pass | `swebench_sympy__sympy-23262` | 0/5 | 0/5 | 0/5 |
| never pass | `swebench_sympy__sympy-23191` | 0/4 | 1/4 | 0/5 |
| never pass | `swebench_sympy__sympy-23117` | 5/5 | 5/5 | 0/5 |
| never pass | `swebench_psf__requests-3362` | 0/5 | 0/5 | 0/5 |

### Interpretation

Across **5 repeats** on **10 instances**, file localization without repo context reached **54.2% pooled exact** (per-instance mean 54.0%), and **7/10** instances named the right file (≥basename) on a majority of samples. A model with no prior exposure would land near chance on arbitrary repo-relative paths — rates this high are **instance-level memorization evidence**.
The per-round swing (50%–60%) confirms the model is **non-deterministic at temperature=0**: single-shot probes are unreliable, which is itself a methodology finding (repeated sampling is required).
Always-pass tasks in REWORK baseline (`swebench_pallets__flask-4992` loc 5/5, `swebench_sympy__sympy-24213` loc 5/5) are both strongly localized, supporting *remembered instances pass; unremembered ones do not* (bimodal fingerprint). Note some never-pass tasks are also localized exactly (e.g. 23117, 24909), i.e. the model knows *which* file but still cannot author the fix — localization memory and solve ability diverge.
Therefore **absolute success rates on this dataset must not be cited as agent capability**; relative A/B comparisons may remain informative under symmetric contamination but with compressed discrimination.
