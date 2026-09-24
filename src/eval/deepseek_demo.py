"""Frozen, public boltons defect demo; not a benchmark or the upstream test suite."""
from dataclasses import asdict
from pathlib import Path
import difflib
import hashlib

import httpx

from src.eval.contracts import EvaluationSpec, PublicTask, TestCase
from src.eval.grader import save_json, tree_hash
from src.execution.docker import DEFAULT_IMAGE

REVISION = "967864f89791509f9eb36b22b4579d36b72a6df2"
REPO = "https://github.com/mahmoud/boltons"
ISSUE = REPO + "/pull/475"
TASK_ID = "boltons-475-strutils-slice"
SOURCE_HASHES = {
    "boltons/strutils.py": "942cf2e33492fa6eb48508d74cd96cf2545dec50c26a2ab361bbf81507317943",
    "LICENSE": "c301912653a8d8c99eab6212aa3aea8d164ea249d8ad53c941e0558a0a5ac1e3",
}
PRICING_URL = "https://api-docs.deepseek.com/quick_start/pricing"
PRICES = {  # USD per million tokens, official page retrieved 2026-09-21.
    "deepseek-flash": {"hit": 0.006, "miss": 0.30, "output": 1.20},
    "deepseek-v4-pro": {"hit": 0.044, "miss": 1.32, "output": 3.96},
}

PUBLIC_TEST = '''import importlib.util
import unittest

s = importlib.util.spec_from_file_location("strutils", "boltons/strutils.py")
m = importlib.util.module_from_spec(s)
s.loader.exec_module(m)

class PublicRegression(unittest.TestCase):
    def test_paragraph_separator(self):
        self.assertEqual(m.indent("a\\u2029b", "> "), "> a\\n> b")

    def test_date_text(self):
        self.assertEqual(m.indent("February 28, 2026", "> "), "> February 28, 2026")

    def test_crlf_control(self):
        self.assertEqual(m.indent("a\\r\\nb", "> "), "> a\\n> b")

if __name__ == "__main__":
    unittest.main()
'''


def make_task(base):
    return PublicTask(TASK_ID,
        "Repair the reported Unicode line-separator defect in boltons/strutils.py. "
        "iter_splitlines and indent should recognize Unicode line/paragraph separators "
        "without splitting ordinary date/number text, and preserve existing empty-line, "
        "CRLF and custom-newline behavior. Only modify boltons/strutils.py. "
        "Inspect the implementation, run the provided public tests before and after editing, "
        "then briefly describe the fix. Do not modify tests or create extra files. "
        "Use python -B for commands so bytecode files are not created. "
        "This is a frozen repository module slice, not a full checkout. "
        "Public check: python -B test_public.py. Network and package installation are unavailable.",
        repo_id=REPO, base_revision=REVISION,
        public_context={"defect_report": ISSUE, "scope": "module slice",
                        "base_hash": tree_hash(base), "editable_paths": ["boltons/strutils.py"]})


def make_spec(base):
    # Frozen BEFORE the paid call. No candidate-generated tests or expected values.
    probes = [
        ("line-separator", ["alpha\u2028beta", "> "], "> alpha\n> beta"),
        ("paragraph-separator", ["alpha\u2029beta", "--"], "--alpha\n--beta"),
        ("date-28", ["February 28, 2026", "> "], "> February 28, 2026"),
        ("number-29", [" 29 and 28", "*"], "* 29 and 28"),
        ("leading-trailing", ["\u2028a\u2029", "  "], "\n  a\n"),
        ("adjacent-unicode", ["a\u2028\u2029b", "+"], "+a\n\n+b"),
        ("mixed-newlines", ["a\r\nb\u2028c\u2029d\re\nf", "-"], "-a\n-b\n-c\n-d\n-e\n-f"),
        ("custom-newline", ["x\u2028y\u2029z", ">", "|"], ">x|>y|>z"),
        ("empty", ["", ">"], ""),
        ("crlf", ["a\r\nb\r\n", "  "], "  a\n  b\n"),
        ("blank-lines", ["\na\n\n", ">"], "\n>a\n\n"),
        ("legacy-separators", ["a\vb\fc\x85d", ">"], ">a\n>b\n>c\n>d"),
        ("whitespace", [" \t\n  ", "+"], "+ \t\n+  "),
        ("literal-backslash", [r"a\u2028b", "-"], r"-a\u2028b"),
        ("unicode-text", ["你好\u2028世界 28\u2029尾部 29", ">"], ">你好\n>世界 28\n>尾部 29"),
        ("empty-margin", ["x\u2029y", ""], "x\ny"),
    ]
    cases = [TestCase(cid, "boltons/strutils.py", "indent", args, value)
             for cid, args, value in probes]
    cases += [TestCase("unrelated-camel", "boltons/strutils.py", "camel2under", ["BasicParseTest"], "basic_parse_test"),
              TestCase("unrelated-bytes", "boltons/strutils.py", "bytes2human", [1024], "1K")]
    return EvaluationSpec(TASK_ID, tree_hash(base), DEFAULT_IMAGE, ("boltons/strutils.py",), tuple(cases))


async def prepare(directory: Path, source_dir: Path | None = None):
    """Fetch only immutable upstream source/license, never PR patches/solutions."""
    directory.mkdir(parents=True, exist_ok=False)
    seed = directory / "seed"
    seed.mkdir()
    files, sources = {}, []
    try:
        async with httpx.AsyncClient(trust_env=False, timeout=60, follow_redirects=True) as http:
            for path, expected_hash in SOURCE_HASHES.items():
                url = f"https://raw.githubusercontent.com/mahmoud/boltons/{REVISION}/{path}"
                if source_dir is not None:
                    content = (Path(source_dir) / path).read_bytes()
                else:
                    response = await http.get(url)
                    response.raise_for_status()
                    content = response.content
                source_hash = hashlib.sha256(content).hexdigest()
                if source_hash != expected_hash:
                    raise ValueError(f"frozen upstream source hash mismatch: {path}")
                files[path] = content
                sources.append(dict(path=path, url=url, sha256=source_hash))
    except Exception as exc:
        save_json(directory / "preparation.json", dict(status="invalid_env", phase="source_preparation",
                  error_kind=type(exc).__name__, model_calls=0))
        raise
    files["test_public.py"] = PUBLIC_TEST.encode()
    for path, content in files.items():
        target = seed / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    task, spec = make_task(files), make_spec(files)
    save_json(directory / "sources.json", dict(repo=REPO, revision=REVISION, report=ISSUE,
              scope="two upstream files plus host-authored public regression tests; not full repository", files=sources))
    save_json(directory / "public-task.json", task.agent_payload())
    save_json(directory / "private-spec.json", asdict(spec))
    save_json(directory / "preparation.json", dict(status="ready", source="verified_local_copy" if source_dir else "https",
              model_calls=0))
    return files, task, spec


def usage_report(attempts, model):
    """Provider counters + price interval, never an asserted account charge."""
    fields = ("prompt_tokens", "completion_tokens", "total_tokens", "prompt_cache_hit_tokens", "prompt_cache_miss_tokens")
    sums = {key: 0 for key in fields}
    missing = set()
    unknown = 0
    for attempt in attempts:
        usage = attempt.get("usage") or {}
        valid = usage.get("provenance") == "provider"
        for key in fields:
            value = usage.get(key)
            if not valid or type(value) is not int or value < 0:
                missing.add(key)
            else:
                sums[key] += value
        if not valid or any(type(usage.get(k)) is not int or usage[k] < 0 for k in fields[:3]):
            unknown += 1
    totals = {k: None if k in missing else v for k, v in sums.items()}
    prices = PRICES.get(model)
    high = None
    if attempts and prices and not missing and totals["prompt_cache_hit_tokens"] + totals["prompt_cache_miss_tokens"] == totals["prompt_tokens"]:
        high = (totals["prompt_cache_hit_tokens"] * prices["hit"] + totals["prompt_cache_miss_tokens"] * prices["miss"]
                + totals["completion_tokens"] * prices["output"]) / 1_000_000
    return dict(model=model, attempts=len(attempts), unknown_usage_attempts=unknown,
                provider_totals=totals, known_subtotals=sums,
                cost_usd=None, cost_provenance="not_reconciled_with_account_billing",
                estimated_cost_usd_range=[high/2, high] if high is not None else None,
                estimate_basis="off-peak/peak interval, excludes account discounts, not an invoice",
                peak_usd_per_million=prices, pricing_source=PRICING_URL, pricing_retrieved="2026-09-21")


def candidate_diff(base, candidate):
    return "".join(line for path in sorted(base.keys() | candidate.keys())
                   if base.get(path) != candidate.get(path)
                   for line in difflib.unified_diff(base.get(path, b"").decode().splitlines(True),
                       candidate.get(path, b"").decode().splitlines(True), fromfile="a/"+path, tofile="b/"+path))
