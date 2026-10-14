"""Zero-model calibration: empty delta and gold delta inside the baseline image."""
import asyncio
import base64
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_swe_task import HOLDOUT, django_nodeids, parse_id_list, prefix_sympy_nodeids, usable_nodeid
from src.eval.image_grader import ImageGrader

ROOTS = [
    ROOT / "docs/upgrade/evidence/A5-harness-preflight-57-remaining16-baseline/tasks",
    ROOT / "docs/upgrade/evidence/A5-harness-preflight-62-history-baseline-retry/tasks",
]


def candidates():
    found = {}
    for root in ROOTS:
        if not root.is_dir():
            continue
        for receipt_path in root.glob("*/receipt.json"):
            task_id = receipt_path.parent.name
            if task_id in HOLDOUT:
                continue
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            if receipt.get("baseline_image_digest"):
                found[task_id] = receipt_path.parent
    return found


def gold_delta(task_dir: Path, paths: list[str]) -> dict:
    known = task_dir / "staging/known-good"
    changed = {}
    for relative in paths:
        file = known / relative
        if file.is_file():
            changed[relative] = base64.b64encode(file.read_bytes()).decode("ascii")
    return {"changed": changed, "deleted": []}


def spec_ids(task_dir: Path):
    receipt = json.loads((task_dir / "receipt.json").read_text(encoding="utf-8"))
    private = json.loads(Path(receipt["private_source_binding"]["path"]).read_text(encoding="utf-8"))
    family = task_dir.name.split("__", 1)[0]
    f2p = parse_id_list(private.get("FAIL_TO_PASS"))
    p2p = parse_id_list(private.get("PASS_TO_PASS"))
    test_paths = receipt["private_source_binding"].get("test_patch_paths") or []
    if family == "django":
        f2p, p2p = django_nodeids(f2p), django_nodeids(p2p)
    if family == "sympy":
        f2p, p2p = prefix_sympy_nodeids(f2p, test_paths), prefix_sympy_nodeids(p2p, test_paths)
    f2p = [node for node in f2p if usable_nodeid(node)]
    p2p = [node for node in p2p if usable_nodeid(node)]
    overlay = {}
    baseline = task_dir / "staging/baseline"
    original = task_dir / "staging/original"
    for relative in receipt["private_source_binding"].get("test_patch_paths") or []:
        updated = baseline / relative
        if not updated.is_file():
            continue
        new = updated.read_bytes()
        old = (original / relative).read_bytes() if (original / relative).is_file() else b""
        if new != old:
            overlay[relative] = base64.b64encode(new).decode("ascii")
    return receipt, family, f2p, p2p, overlay


async def one(task_id: str, task_dir: Path) -> dict:
    receipt, family, f2p, p2p, overlay = spec_ids(task_dir)
    grader = ImageGrader()
    common = dict(
        image=receipt["baseline_image_digest"], test_overlay=overlay,
        django=family == "django", sympy=False, timeout=600,
    )
    empty = await grader.evaluate(delta={"changed": {}, "deleted": []}, f2p=f2p, p2p=p2p, **common)
    gold = await grader.evaluate(
        delta=gold_delta(task_dir, receipt["private_source_binding"].get("gold_patch_paths") or []),
        f2p=f2p, p2p=p2p, **common,
    )
    gold_cases = {case["nodeid"]: case["outcome"] for case in gold.get("cases") or []}
    excluded = [node for node in p2p if gold_cases.get(node) != "passed"]
    kept = [node for node in p2p if node not in excluded]
    empty_cases = {case["nodeid"]: case["outcome"] for case in empty.get("cases") or []}
    f2p_fails_empty = all(empty_cases.get(node) != "passed" for node in f2p) and bool(f2p)
    f2p_passes_gold = all(gold_cases.get(node) == "passed" for node in f2p) and bool(f2p)
    p2p_ok_empty = all(empty_cases.get(node) == "passed" for node in kept)
    accepted = f2p_fails_empty and f2p_passes_gold and p2p_ok_empty
    return {
        "id": task_id,
        "family": family,
        "accepted": accepted,
        "f2p_total": len(f2p),
        "p2p_total": len(p2p),
        "p2p_excluded": excluded,
        "empty_f2p": empty.get("f2p_passed"),
        "empty_p2p": sum(1 for node in kept if empty_cases.get(node) == "passed"),
        "empty_p2p_total": len(kept),
        "gold_f2p": gold.get("f2p_passed"),
        "gold_p2p": sum(1 for node in kept if gold_cases.get(node) == "passed"),
        "gold_reason": gold.get("reason"),
        "empty_reason": empty.get("reason"),
        "receipt": str(task_dir.relative_to(ROOT)).replace("\\", "/"),
    }


async def main():
    out = ROOT / "runs/sprint2-calibrate/results.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out.exists():
        for line in out.read_text(encoding="utf-8").splitlines():
            if line.strip():
                done.add(json.loads(line)["id"])
    wanted = sys.argv[1:]
    for task_id, task_dir in sorted(candidates().items()):
        if task_id in done or (wanted and task_id not in wanted):
            continue
        row = await one(task_id, task_dir)
        with out.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row) + "\n")
        print(json.dumps({key: row[key] for key in ("id", "accepted", "empty_f2p", "gold_f2p", "empty_p2p", "gold_p2p", "empty_reason", "gold_reason")}), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
