"""A5-main inventory recomputed from disk: tags, input sha, slot counts, costs, check summary. Read-only.

Writes runs/a5-main-logs/inventory.json and prints it. Exits non-zero when an input sha differs from the freeze
record. Reads no private task data.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.handoff_sha import handoff_sha256  # noqa: E402

AGENT = ROOT.parent / "coding-agent"
RUNS = ROOT / "runs" / "a5-main"
VOID = ROOT / "runs" / "a5-main-void"
HALTED = ROOT / "runs" / "a5-main-halted"
OUT = ROOT / "runs" / "a5-main-logs" / "inventory.json"

HARNESS_TAGS = ("a5-main-freeze", "a5-main-freeze-r1", "a5-main-freeze-r2", "a5-main-freeze-r3", "a5-main-freeze-r4")
AGENT_TAGS = ("a5-main-freeze",)

FROZEN = {
    "configs/sprint/main-targets.yaml": "3556a5fdfac8b7d4ac2b631a31e2a7951312523aff605014f3b32eaf184738a4",
    "docs/sprint/main-accepted-ids.txt": "d71cb17adb44fd06f71bf8b0f8babcac12ea839354f1dcec30aae2ffa719b730",
    "configs/sprint/b0-v2.yaml": "ddf53b2db293bf03c7a099a43a34ea96aee5ecca365d9b8b4f11d66afb344e60",
    "docs/sprint/memory-source-runs.json": "984826707e8f69ad9b900134bd244c6056f2d8860f3036a3606bfc60b4bcb450",
    "docs/sprint/main-b0-runs.json": "fe0f47b8df67730a0335d7109631dc09bc4d6b5d19a601acfec0963f5dcb1f8c",
    "docs/sprint/b2-predicted-injection.json": "5d858eb4f3ab368fc655b310168e2c77de311ddfee4f77c0928e4d08ba79e3e5",
}
CARDS = AGENT / "benchmarks" / "a5" / "memory-cards-v6.jsonl"
CARDS_FROZEN = "3416eb9d8f6119081330fb3b0a2d612b8fde4678d6ec1c73a7fc681cedfcfc70"

GROUPS = {"b0_r1_r3": ("b0", (1, 2, 3)), "b2_r1_r3": ("b2", (1, 2, 3)), "b0_r4": ("b0", (4,))}

# (revision, commit the canary ran on, directory root, run dirs relative to that root)
CANARIES = [
    ("修订 0", "02c8671", VOID / "r1-tool-py36", ["django__django-13964/b0/r1", "scikit-learn__scikit-learn-13142/b0/r1"]),
    ("修订 0", "02c8671", HALTED, ["sphinx-doc__sphinx-8593/b0/r1"]),
    ("修订 1", "fb26dbd", VOID / "r1-tool-py36", ["sphinx-doc__sphinx-8593/b0/r1"]),
    ("修订 2", "2f28232", VOID / "r2-no-issue", ["scikit-learn__scikit-learn-14053/b0/r1", "django__django-13964/b0/r1",
                                                  "pytest-dev__pytest-7490/b0/r1", "django__django-16527/b0/r1"]),
    ("修订 3", "1707d23", RUNS, ["django__django-13964/b0/r1", "pytest-dev__pytest-7205/b0/r1",
                                 "scikit-learn__scikit-learn-13142/b0/r1", "sphinx-doc__sphinx-8593/b0/r1",
                                 "sympy__sympy-16766/b0/r1"]),
]
SLOT = re.compile(r"^r(\d+)$")
INFRA_SLOT = re.compile(r"^r(\d+)\.infra\d+$")


def git(repo: Path, *args) -> str:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True).stdout.strip()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def cost(summary: dict) -> Decimal:
    return Decimal(str(summary.get("cost_cny") or "0"))


def run_dirs(root: Path):
    """(task, phase, slot name, summary) for every run directory with a summary.json under root/<task>/<phase>/."""
    for summary_path in sorted(root.glob("*/*/*/summary.json")):
        slot_dir = summary_path.parent
        yield slot_dir.parent.parent.name, slot_dir.parent.name, slot_dir.name, load(summary_path)


def group_of(phase: str, slot: str):
    match = SLOT.match(slot) or INFRA_SLOT.match(slot)
    if not match:
        return None
    repeat = int(match.group(1))
    for name, (group_phase, repeats) in GROUPS.items():
        if phase == group_phase and repeat in repeats:
            return name
    return None


def mean(total: Decimal, n: int) -> str:
    return str((total / n).quantize(Decimal("0.001"))) if n else None


def inventory() -> tuple[dict, list[str]]:
    problems = []
    tags = {
        "coding-harness": {tag: git(ROOT, "rev-list", "-n1", tag) for tag in HARNESS_TAGS},
        "coding-agent": {tag: git(AGENT, "rev-list", "-n1", tag) for tag in AGENT_TAGS},
    }

    inputs = {}
    for relative, frozen in FROZEN.items():
        path = ROOT / relative
        lf = handoff_sha256(path)
        inputs[relative] = {"handoff_sha256": lf, "frozen": frozen, "match": lf == frozen}
        if lf != frozen:
            problems.append(relative + " hashes to " + lf + ", freeze record says " + frozen)
    manifest = load(CARDS.with_name("memory-cards-v6.manifest.json"))
    raw = hashlib.sha256(CARDS.read_bytes()).hexdigest()
    card_rows = [line for line in CARDS.read_text(encoding="utf-8").splitlines() if line.strip()]
    inputs["coding-agent/benchmarks/a5/memory-cards-v6.jsonl"] = {
        "cards_sha256_manifest": manifest.get("cards_sha256"), "cards_sha256_file": raw, "frozen": CARDS_FROZEN,
        "cards": len(card_rows), "manifest_status": manifest.get("status"),
        "match": raw == manifest.get("cards_sha256") == CARDS_FROZEN,
    }
    if not inputs["coding-agent/benchmarks/a5/memory-cards-v6.jsonl"]["match"]:
        problems.append("cards_sha256 differs: manifest " + str(manifest.get("cards_sha256")) + ", file " + raw)

    groups = {name: {"completed": 0, "infra_retired": [], "cost_completed": Decimal(0), "cost_infra": Decimal(0)} for name in GROUPS}
    rows = list(run_dirs(RUNS))
    for task, phase, slot, summary in rows:
        name = group_of(phase, slot)
        if name is None:
            problems.append("unexpected run directory " + "/".join((task, phase, slot)))
            continue
        if SLOT.match(slot):
            groups[name]["completed"] += 1
            groups[name]["cost_completed"] += cost(summary)
        else:
            groups[name]["infra_retired"].append("/".join((task, phase, slot)))
            groups[name]["cost_infra"] += cost(summary)
    for name, group in groups.items():
        total = group["cost_completed"] + group["cost_infra"]
        group["cost_total"] = str(total)
        group["mean_per_completed_slot"] = mean(total, group["completed"])
        group["mean_per_run_dir"] = mean(total, group["completed"] + len(group["infra_retired"]))
        group["cost_completed"] = str(group["cost_completed"])
        group["cost_infra"] = str(group["cost_infra"])

    regraded = [{"run": "/".join((task, phase, slot)), "grader_candidate_error": summary.get("grader_candidate_error"),
                 "missing_regrade": bool(summary.get("missing_regrade")), "timeout_regrade": bool(summary.get("timeout_regrade")),
                 "solved": summary.get("solved")}
                for task, phase, slot, summary in rows if summary.get("missing_regrade") or summary.get("timeout_regrade")]

    void = {}
    for sub in sorted(path.name for path in VOID.iterdir() if path.is_dir()):
        void_rows = list(run_dirs(VOID / sub))
        record = load(VOID / sub / "void-runs.json")
        disk = sum((cost(summary) for *_, summary in void_rows), Decimal(0))
        listed = sum((Decimal(str(row["cost_cny"])) for row in record["runs"]), Decimal(0))
        void[sub] = {"run_dirs": len(void_rows), "infra_dirs": sum(1 for _, _, slot, _ in void_rows if INFRA_SLOT.match(slot)),
                     "cost": str(disk), "void_runs_json_runs": len(record["runs"]), "void_runs_json_cost": str(listed)}
        if disk != listed or len(void_rows) != len(record["runs"]):
            problems.append("void " + sub + " disk and void-runs.json differ")
    halted_rows = list(run_dirs(HALTED))
    halted = {"run_dirs": len(halted_rows), "cost": str(sum((cost(summary) for *_, summary in halted_rows), Decimal(0)))}

    canaries = []
    for revision, commit, root, runs in CANARIES:
        for run in runs:
            summary = load(root / run / "summary.json")
            canaries.append({"revision": revision, "commit": commit, "where": root.relative_to(ROOT).as_posix(), "run": run,
                             "cost": str(cost(summary)), "model_calls": summary.get("model_calls")})

    valid_total = sum((Decimal(group["cost_total"]) for group in groups.values()), Decimal(0))
    void_total = sum((Decimal(item["cost"]) for item in void.values()), Decimal(0))
    sprint6_total = valid_total + void_total + Decimal(halted["cost"])

    all_rows = rows
    checks = {
        "runs_checked": len(all_rows),
        "isolation_failed": sum(1 for *_, s in all_rows if s.get("answer_isolation_pass") is False or s.get("status") == "answer_isolation_failed"),
        "harness_tool_errors": sum(int(s.get("harness_tool_errors") or 0) for *_, s in all_rows),
        "missing_unclassified": sum(1 for *_, s in all_rows if (s.get("grader_ids") or {}).get("missing") and not s.get("grader_candidate_error")),
        "grader_reason_unclassified": sum(1 for *_, s in all_rows if s.get("status") != "infra_error"
                                          and (s.get("grader_ids") or {}).get("reason") and not s.get("grader_candidate_error")),
    }
    stats_path = ROOT / "runs" / "a5-main-logs" / "b2-stats.json"
    if stats_path.is_file():
        stats = load(stats_path)
        checks["b2_stats"] = {
            "injection_runs_checked": stats["injection"]["runs_checked"],
            "injection_runs_agree": stats["injection"]["runs_agree"],
            "audit": {key: len(value) for key, value in stats["audit"].items()},
            "spent_total_cny": stats.get("spent_total_cny"),
        }
        if stats.get("spent_total_cny") != str(valid_total):
            problems.append("b2-stats spent_total_cny " + str(stats.get("spent_total_cny")) + " differs from " + str(valid_total))

    report = {
        "tags": tags,
        "inputs": inputs,
        "slots": groups,
        "regraded": regraded,
        "void": void,
        "halted": halted,
        "canaries": canaries,
        "costs": {"valid_runs_a5_main": str(valid_total), "void_total": str(void_total), "halted": halted["cost"],
                  "sprint6_total": str(sprint6_total)},
        "checks": checks,
        "problems": problems,
    }
    return report, problems


def main():
    report, problems = inventory()
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if problems:
        raise SystemExit("inventory problems:\n" + "\n".join(problems))


if __name__ == "__main__":
    main()
