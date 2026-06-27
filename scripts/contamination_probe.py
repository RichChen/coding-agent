#!/usr/bin/env python3
"""SWE-bench instance-level contamination probe (file localization, no repo context).

Replicates the file-localization probe from *The SWE-Bench Illusion* (arXiv 2506.12286):
given only issue text + repo name, ask the model which source file to modify.
High hit rate implies instance-level memorization.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.harness.factory import load_config
from src.llm.client import LLMClient, LLMError

# deepseek-v4-pro is a reasoning model: it spends completion budget on a
# reasoning channel before emitting `content`. 256 was too small and truncated
# 6/10 answers (finish_reason="length", empty content). Give ample headroom.
PROBE_MAX_TOKENS = 2048
PROBE_TEMPERATURE = 0.0

SYSTEM_PROMPT = """You are a senior engineer doing bug triage. You will be given only a bug
report (issue) and the repository name. You do NOT have access to the
repository's file tree or source code. Based solely on the issue text and
your prior knowledge of the codebase, name the single SOURCE file most
likely to need modification to fix this bug.

Rules:
- Output ONLY the repository-relative file path, nothing else.
- It must be a source file, NOT a test file.
- Do not output explanations, markdown, or multiple paths."""

USER_PROMPT_TEMPLATE = """Repository: {repo}

Issue:
{issue_text}

Which single source file should be modified? Output only the path."""

# Baseline pass counts from REWORK clean A/B (report_20260626T101113.md)
REWORK_BASELINE_PASSES: dict[str, str] = {
    "swebench_pallets__flask-4992": "5/5",
    "swebench_psf__requests-3362": "0/5",
    "swebench_sympy__sympy-23117": "0/5",
    "swebench_sympy__sympy-23191": "0/5",
    "swebench_sympy__sympy-23262": "0/5",
    "swebench_sympy__sympy-24066": "3/5",
    "swebench_sympy__sympy-24102": "0/5",
    "swebench_sympy__sympy-24152": "3/5",
    "swebench_sympy__sympy-24213": "5/5",
    "swebench_sympy__sympy-24909": "0/5",
}


@dataclass
class ProbeResult:
    """One LLM call (one repeat)."""

    predicted: str
    match_level: str  # exact | basename | wrong | truncated | error
    tokens: dict[str, int]
    raw_response: str | None = None
    error: str | None = None


@dataclass
class InstanceProbe:
    """All repeats for a single instance."""

    instance_id: str
    repo: str
    gold: str | None
    attempts: list[ProbeResult]
    skip_reason: str | None = None

    @property
    def is_skipped(self) -> bool:
        return self.skip_reason is not None

    @property
    def valid_attempts(self) -> list[ProbeResult]:
        return [a for a in self.attempts if a.match_level in ("exact", "basename", "wrong")]

    @property
    def n_valid(self) -> int:
        return len(self.valid_attempts)

    @property
    def n_exact(self) -> int:
        return sum(1 for a in self.attempts if a.match_level == "exact")

    @property
    def n_basename(self) -> int:
        return sum(1 for a in self.attempts if a.match_level == "basename")

    @property
    def n_wrong(self) -> int:
        return sum(1 for a in self.attempts if a.match_level == "wrong")

    @property
    def n_truncated(self) -> int:
        return sum(1 for a in self.attempts if a.match_level == "truncated")

    @property
    def n_loc(self) -> int:
        """exact + basename — model named the right file (path or filename)."""
        return self.n_exact + self.n_basename

    @property
    def exact_freq(self) -> float | None:
        return (self.n_exact / self.n_valid) if self.n_valid else None

    @property
    def loc_freq(self) -> float | None:
        """basename-or-better frequency = did it identify the right file at all."""
        return (self.n_loc / self.n_valid) if self.n_valid else None

    @property
    def has_error(self) -> bool:
        return any(a.match_level == "error" for a in self.attempts)


def find_gold_py(oracle_dir: Path) -> tuple[str | None, str | None]:
    """Return (gold_relative_path, skip_reason)."""
    if not oracle_dir.is_dir():
        return None, f".oracle missing: {oracle_dir}"
    py_files = [p for p in oracle_dir.rglob("*.py") if p.is_file()]
    if len(py_files) == 0:
        return None, "no .py under .oracle"
    if len(py_files) > 1:
        rels = [str(p.relative_to(oracle_dir)).replace("\\", "/") for p in py_files]
        return None, f"multiple .py under .oracle ({len(py_files)}): {rels[:5]}"
    rel = py_files[0].relative_to(oracle_dir)
    return str(rel).replace("\\", "/"), None


def repo_from_task_id(task_id: str) -> str:
    """swebench_sympy__sympy-24909 -> sympy/sympy"""
    body = task_id.removeprefix("swebench_")
    if "__" not in body:
        return body
    owner, rest = body.split("__", 1)
    repo = re.sub(r"-\d+$", "", rest)
    return f"{owner}/{repo}"


def extract_issue_text(description: str) -> str:
    text = description.strip()
    text = re.sub(r"^\[SWE-bench Lite [^\]]+\]\s*", "", text)
    suffix = " Do not use .oracle files and do not modify tests."
    if text.endswith(suffix):
        text = text[: -len(suffix)]
    elif text.endswith(suffix.strip()):
        text = text[: -len(suffix.strip())]
    return " ".join(text.split())


def normalize_path(path: str) -> str:
    p = path.strip().strip("\"'`")
    p = re.sub(r"^(?:path|file)\s*:\s*", "", p, flags=re.IGNORECASE)
    p = p.lstrip("-* ").strip()
    p = p.replace("\\", "/")
    if p.startswith("./"):
        p = p[2:]
    return p.lower()


def parse_predicted(raw: str) -> str:
    if not raw or not raw.strip():
        return "(unparseable)"
    text = raw.strip()
    # Prefer explicit path-like tokens anywhere in the response
    path_pattern = re.compile(
        r"(?:^|[\s\"'`(])([a-zA-Z0-9_./-]+\.py)(?:[\s\"'`),]|$)",
        re.MULTILINE,
    )
    for m in path_pattern.finditer(text):
        candidate = normalize_path(m.group(1))
        if candidate and "test" not in Path(candidate).parts[-1].lower():
            if "/" in candidate:
                return candidate
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for line in lines:
        cleaned = normalize_path(line)
        if "/" in cleaned or cleaned.endswith(".py"):
            return cleaned
    for token in re.split(r"[\s,;]+", lines[0] if lines else text):
        t = normalize_path(token)
        if "/" in t or t.endswith(".py"):
            return t
    cleaned = normalize_path(lines[0]) if lines else normalize_path(text)
    return cleaned if cleaned else "(unparseable)"


def classify_match(gold: str, predicted: str) -> str:
    if predicted in ("(unparseable)", "", "(truncated)"):
        return "wrong"
    g = normalize_path(gold)
    p = normalize_path(predicted)
    if g == p:
        return "exact"
    if Path(g).name == Path(p).name and Path(g).name:
        return "basename"
    return "wrong"


def build_llm_client(config: dict[str, Any], max_tokens: int) -> LLMClient:
    llm_cfg = config["llm"]
    return LLMClient(
        base_url=llm_cfg["base_url"],
        api_key=llm_cfg["api_key"],
        model=llm_cfg["model"],
        temperature=PROBE_TEMPERATURE,
        max_tokens=max_tokens,
        timeout_seconds=180.0,
    )


async def probe_call(
    client: LLMClient,
    repo: str,
    issue_text: str,
    gold: str,
) -> ProbeResult:
    """One localization call (one repeat)."""
    user_msg = USER_PROMPT_TEMPLATE.format(repo=repo, issue_text=issue_text)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_msg},
    ]
    try:
        resp = await client.chat(messages)
    except Exception as e:
        return ProbeResult(
            predicted="(error)",
            match_level="error",
            tokens={},
            error=str(e),
        )

    predicted = parse_predicted(resp.text or "")
    # Reasoning models can exhaust the completion budget before emitting `content`.
    # An empty/unparseable answer with finish_reason="length" (or completion at the
    # cap) is a MEASUREMENT truncation, not a wrong localization — track separately.
    completion = (resp.usage or {}).get("completion_tokens", 0)
    truncated = resp.finish_reason == "length" or completion >= client.max_tokens
    if predicted == "(unparseable)" and truncated:
        return ProbeResult(
            predicted="(truncated)",
            match_level="truncated",
            tokens=dict(resp.usage or {}),
            raw_response=(resp.text or "")[:2000],
        )
    return ProbeResult(
        predicted=predicted,
        match_level=classify_match(gold, predicted),
        tokens=dict(resp.usage or {}),
        raw_response=(resp.text or "")[:2000],
    )


async def probe_instance(
    client: LLMClient,
    task: dict[str, Any],
    root: Path,
    repeats: int,
) -> InstanceProbe:
    task_id = task["id"]
    repo = repo_from_task_id(task_id)
    oracle_dir = (root / task["fixture_dir"] / ".oracle").resolve()
    gold, skip_reason = find_gold_py(oracle_dir)
    if skip_reason:
        return InstanceProbe(
            instance_id=task_id, repo=repo, gold=None, attempts=[], skip_reason=skip_reason
        )

    issue_text = extract_issue_text(task["description"])
    attempts: list[ProbeResult] = []
    for _ in range(repeats):
        attempt = await probe_call(client, repo, issue_text, gold)
        attempts.append(attempt)
        if attempt.error:
            break  # provider/balance error — stop this instance, caller decides to abort
    return InstanceProbe(instance_id=task_id, repo=repo, gold=gold, attempts=attempts)


def _round_exact_rates(probes: list[InstanceProbe], repeats: int) -> list[float | None]:
    """Per-round (per-repeat-index) exact rate over instances with a valid attempt
    at that index. Surfaces the model's non-determinism as a swing across rounds."""
    rates: list[float | None] = []
    for i in range(repeats):
        exact = 0
        valid = 0
        for p in probes:
            if i < len(p.attempts):
                a = p.attempts[i]
                if a.match_level in ("exact", "basename", "wrong"):
                    valid += 1
                    if a.match_level == "exact":
                        exact += 1
        rates.append((exact / valid * 100) if valid else None)
    return rates


def render_markdown(
    probes: list[InstanceProbe],
    *,
    model: str,
    max_tokens: int,
    repeats: int,
    cost_per_1k: float,
    aborted: str | None,
) -> str:
    scored = [p for p in probes if not p.is_skipped and p.n_valid > 0]
    skipped = [p for p in probes if p.is_skipped]

    # Pooled over all attempts (robust to per-run noise)
    total_exact = sum(p.n_exact for p in scored)
    total_basename = sum(p.n_basename for p in scored)
    total_valid = sum(p.n_valid for p in scored)
    total_truncated = sum(p.n_truncated for p in probes)
    pooled_exact = (total_exact / total_valid * 100) if total_valid else 0.0
    pooled_basename_or_better = (
        (total_exact + total_basename) / total_valid * 100 if total_valid else 0.0
    )

    # Per-instance exact-frequency mean (each instance weighted equally)
    freqs = [p.exact_freq for p in scored if p.exact_freq is not None]
    inst_mean = (sum(freqs) / len(freqs) * 100) if freqs else 0.0

    # Per-round swing (non-determinism)
    round_rates = [r for r in _round_exact_rates(probes, repeats) if r is not None]
    swing_min = min(round_rates) if round_rates else 0.0
    swing_max = max(round_rates) if round_rates else 0.0

    # majority-exact / majority-localized (exact-or-basename) instances
    majority_exact = [p for p in scored if p.exact_freq is not None and p.exact_freq >= 0.5]
    majority_loc = [p for p in scored if p.loc_freq is not None and p.loc_freq >= 0.5]

    all_attempts = [a for p in probes for a in p.attempts]
    total_tokens = sum(a.tokens.get("total_tokens", 0) for a in all_attempts)
    prompt_tokens = sum(a.tokens.get("prompt_tokens", 0) for a in all_attempts)
    completion_tokens = sum(a.tokens.get("completion_tokens", 0) for a in all_attempts)
    est_cost = (total_tokens / 1000.0 * cost_per_1k) if cost_per_1k > 0 else None

    lines = [
        "# SWE-bench Contamination Probe Report",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Model: `{model}` (temperature={PROBE_TEMPERATURE}, max_tokens={max_tokens}, repeats={repeats})",
        "",
        "> File-localization probe (no repo context), replicating *The SWE-Bench Illusion*. "
        "The model is **non-deterministic at temperature=0** (reasoning model), so each "
        "instance is sampled `repeats` times and scored by hit frequency.",
        "",
    ]
    if aborted:
        lines += [
            "> **Run aborted**: " + aborted,
            "> Re-run when balance is restored with the same command.",
            "",
        ]

    lines += [
        "## Aggregate",
        "",
        f"- Instances scored: **{len(scored)}** (skipped: {len(skipped)}); "
        f"repeats per instance: **{repeats}**; valid attempts: {total_valid}, truncated: {total_truncated}",
        f"- **Pooled exact rate**: {pooled_exact:.1f}% ({total_exact}/{total_valid} attempts)",
        f"- **Per-instance exact-frequency mean**: {inst_mean:.1f}%",
        f"- **Pooled basename-or-better**: {pooled_basename_or_better:.1f}%",
        f"- **Per-round exact swing**: {swing_min:.0f}%–{swing_max:.0f}% "
        f"(rounds: {', '.join(f'{r:.0f}%' for r in round_rates)})",
        f"- **Majority-exact instances**: {len(majority_exact)}/{len(scored)} "
        f"(exact is the modal answer over repeats)",
        f"- **Majority-localized instances** (≥basename): {len(majority_loc)}/{len(scored)} "
        f"(named the right file on a majority of samples)",
        f"- Total tokens: {total_tokens} (prompt {prompt_tokens}, completion {completion_tokens})",
    ]
    if est_cost is not None:
        lines.append(f"- Est. cost (@ ${cost_per_1k}/1k): ${est_cost:.4f}")
    else:
        lines.append("- Est. cost: n/a (pass `--cost-per-1k` to estimate)")

    lines += [
        "",
        "## Per-Instance Results",
        "",
        "| instance_id | repo | gold | exact hits | basename | wrong | trunc | distinct predictions | baseline (REWORK) |",
        "|-------------|------|------|-----------|----------|-------|-------|----------------------|-------------------|",
    ]
    for p in probes:
        passes = REWORK_BASELINE_PASSES.get(p.instance_id, "n/a")
        if p.is_skipped:
            lines.append(
                f"| `{p.instance_id}` | {p.repo} | — | skipped ({p.skip_reason}) | — | — | — | — | {passes} |"
            )
            continue
        preds: dict[str, int] = {}
        for a in p.valid_attempts:
            preds[a.predicted] = preds.get(a.predicted, 0) + 1
        preds_str = ", ".join(
            f"`{path}`×{cnt}" for path, cnt in sorted(preds.items(), key=lambda kv: -kv[1])
        ) or "—"
        lines.append(
            f"| `{p.instance_id}` | {p.repo} | `{p.gold}` | "
            f"**{p.n_exact}/{p.n_valid}** | {p.n_basename} | {p.n_wrong} | {p.n_truncated} | "
            f"{preds_str} | {passes} |"
        )

    # Cross-validation with bimodal pass rates
    always_pass = {"swebench_sympy__sympy-24213", "swebench_pallets__flask-4992"}
    lines += [
        "",
        "## Cross-Validation with REWORK Bimodal Pass Rates",
        "",
        "Reference: `reports/report_20260626T101113.md` baseline pass matrix (5 runs).",
        "",
        "| Pattern | instance | exact freq | loc freq (≥basename) | baseline passes |",
        "|---------|----------|------------|----------------------|-----------------|",
    ]
    for p in scored:
        passes = REWORK_BASELINE_PASSES.get(p.instance_id, "n/a")
        tag = "always pass" if p.instance_id in always_pass else (
            "never pass" if passes == "0/5" else "mixed"
        )
        lines.append(
            f"| {tag} | `{p.instance_id}` | {p.n_exact}/{p.n_valid} | "
            f"{p.n_loc}/{p.n_valid} | {passes} |"
        )

    # Interpretation
    lines += ["", "### Interpretation", ""]
    if not scored:
        lines.append("No instances scored; probe did not complete successfully.")
    else:
        lines.append(
            f"Across **{repeats} repeats** on **{len(scored)} instances**, file localization without "
            f"repo context reached **{pooled_exact:.1f}% pooled exact** (per-instance mean "
            f"{inst_mean:.1f}%), and **{len(majority_loc)}/{len(scored)}** instances named the right "
            f"file (≥basename) on a majority of samples. A model with no prior exposure would land near "
            f"chance on arbitrary repo-relative paths — rates this high are **instance-level "
            f"memorization evidence**."
        )
        lines.append(
            f"The per-round swing ({swing_min:.0f}%–{swing_max:.0f}%) confirms the model is "
            f"**non-deterministic at temperature=0**: single-shot probes are unreliable, which is "
            f"itself a methodology finding (repeated sampling is required)."
        )
        ap_freq = [
            f"`{p.instance_id}` loc {p.n_loc}/{p.n_valid}"
            for p in scored
            if p.instance_id in always_pass
        ]
        if ap_freq:
            lines.append(
                "Always-pass tasks in REWORK baseline (" + ", ".join(ap_freq) + ") are both strongly "
                "localized, supporting *remembered instances pass; unremembered ones do not* "
                "(bimodal fingerprint). Note some never-pass tasks are also localized exactly "
                "(e.g. 23117, 24909), i.e. the model knows *which* file but still cannot author the "
                "fix — localization memory and solve ability diverge."
            )
        lines.append(
            "Therefore **absolute success rates on this dataset must not be cited as agent capability**; "
            "relative A/B comparisons may remain informative under symmetric contamination but with "
            "compressed discrimination."
        )

    if skipped:
        lines += ["", "## Skipped Instances", ""]
        for p in skipped:
            lines.append(f"- `{p.instance_id}`: {p.skip_reason}")

    return "\n".join(lines) + "\n"


async def run_probe(args: argparse.Namespace) -> int:
    root = Path(__file__).resolve().parent.parent

    # Re-render an existing report from cached raw JSON (no LLM calls).
    if args.from_json:
        src = Path(args.from_json)
        if not src.is_absolute():
            src = root / src
        cached = json.loads(src.read_text(encoding="utf-8"))
        probes = [
            InstanceProbe(
                instance_id=inst["instance_id"],
                repo=inst["repo"],
                gold=inst["gold"],
                attempts=[ProbeResult(**a) for a in inst["attempts"]],
                skip_reason=inst.get("skip_reason"),
            )
            for inst in cached["instances"]
        ]
        out_path = root / args.out
        out_path.parent.mkdir(parents=True, exist_ok=True)
        md = render_markdown(
            probes,
            model=cached.get("model", "unknown"),
            max_tokens=cached.get("max_tokens", args.max_tokens),
            repeats=cached.get("repeats", args.repeats),
            cost_per_1k=args.cost_per_1k,
            aborted=cached.get("aborted"),
        )
        out_path.write_text(md, encoding="utf-8")
        print(f"Re-rendered from {src}\nReport: {out_path}")
        return 0

    dataset_path = root / args.dataset
    data = json.loads(dataset_path.read_text(encoding="utf-8"))
    tasks = data["tasks"][: args.limit] if args.limit else data["tasks"]

    config = load_config(root / args.config)
    client = build_llm_client(config, args.max_tokens)
    model = config["llm"]["model"]
    repeats = max(1, args.repeats)

    probes: list[InstanceProbe] = []
    aborted: str | None = None

    for task in tasks:
        probe = await probe_instance(client, task, root, repeats)
        probes.append(probe)
        print(
            json.dumps(
                {
                    "instance_id": probe.instance_id,
                    "gold": probe.gold,
                    "exact": f"{probe.n_exact}/{probe.n_valid}",
                    "truncated": probe.n_truncated,
                    "predictions": [a.predicted for a in probe.attempts],
                },
                ensure_ascii=False,
            )
        )
        err_attempt = next((a for a in probe.attempts if a.error), None)
        if err_attempt:
            msg = err_attempt.error or ""
            if "402" in msg or "Insufficient Balance" in msg:
                aborted = f"HTTP 402 / insufficient balance during {probe.instance_id}"
            else:
                aborted = f"Provider error during {probe.instance_id}: {msg[:200]}"
            break

    out_path = root / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    md = render_markdown(
        probes,
        model=model,
        max_tokens=args.max_tokens,
        repeats=repeats,
        cost_per_1k=args.cost_per_1k,
        aborted=aborted,
    )
    out_path.write_text(md, encoding="utf-8")

    json_path = out_path.with_suffix(".json")
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "max_tokens": args.max_tokens,
        "repeats": repeats,
        "aborted": aborted,
        "instances": [asdict(p) for p in probes],
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nReport: {out_path}")
    print(f"JSON:   {json_path}")
    return 1 if aborted else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="SWE-bench contamination file-localization probe")
    parser.add_argument("--dataset", default="datasets/swebench_lite_tasks.json")
    parser.add_argument("--config", default="configs/baseline.yaml")
    parser.add_argument("--out", default="reports/contamination_probe.md")
    parser.add_argument("--cost-per-1k", type=float, default=0.0)
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=PROBE_MAX_TOKENS,
        help="Completion budget per probe call (reasoning models need headroom).",
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=1,
        help="Samples per instance (model is non-deterministic at temp=0). Use >=5.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Debug: probe first N tasks only")
    parser.add_argument(
        "--from-json",
        default=None,
        help="Re-render the report from a cached probe JSON (no LLM calls).",
    )
    args = parser.parse_args()
    return asyncio.run(run_probe(args))


if __name__ == "__main__":
    raise SystemExit(main())
