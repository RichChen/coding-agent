"""Zero-model empty/gold calibration on clean images. Does not call a model."""
from __future__ import annotations

import asyncio
import base64
import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.run_swe_task import grader_spec  # noqa: E402
from src.eval.image_grader import ImageGrader  # noqa: E402

OUT = ROOT / "docs" / "sprint" / "clean-calibration"


def gold_delta(task: dict, test_paths: tuple[str, ...]) -> dict:
    staging = (ROOT / task["baseline"]).parent
    binding = json.loads((staging / "gold-binding.json").read_text(encoding="utf-8"))
    gold_root = staging / "known-good"
    changed = {}
    for relative in binding["changed_paths"]:
        if relative in test_paths:
            continue
        path = gold_root / relative
        if path.is_file():
            changed[relative] = base64.b64encode(path.read_bytes()).decode("ascii")
    return {"changed": changed, "deleted": []}


def counts(evaluation: dict, f2p: list[str], p2p: list[str]) -> dict:
    by_id = {case.get("nodeid"): case.get("outcome") for case in evaluation.get("cases") or []}
    return {
        "f2p_passed": sum(1 for node in f2p if by_id.get(node) == "passed"),
        "f2p_total": len(f2p),
        "p2p_passed": sum(1 for node in p2p if by_id.get(node) == "passed"),
        "p2p_total": len(p2p),
        "outcomes": {node: by_id.get(node) for node in f2p + p2p},
    }


def sklearn_import(image: str) -> bool:
    result = subprocess.run(
        ["docker", "--context", "desktop-linux", "run", "--rm", "--network", "none", image,
         "/bin/sh", "-c", "cp -a /opt/repo/. /workspace/ && /usr/local/bin/python -c 'import sklearn; print(sklearn.__file__)'"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180,
    )
    return result.returncode == 0 and b"/opt/repo" not in result.stdout and b"sklearn" in result.stdout


async def one(task: dict) -> dict:
    clean = json.loads((ROOT / "docs/sprint/clean-images" / (task["id"] + ".json")).read_text(encoding="utf-8"))
    spec = grader_spec(task)
    f2p = [node for node in spec.expected_nodeids if node not in spec.baseline_passed]
    p2p = list(spec.baseline_passed)
    image = clean["clean_image_digest"]
    grader = ImageGrader()
    empty = await grader.evaluate(
        image=image, delta={"changed": {}, "deleted": []}, test_overlay=spec.test_overlay,
        f2p=f2p, p2p=p2p, django=task["family"] == "django", sympy=False,
        timeout=float(task.get("grader_timeout_seconds", 600)),
    )
    gold = await grader.evaluate(
        image=image, delta=gold_delta(task, spec.test_paths), test_overlay=spec.test_overlay,
        f2p=f2p, p2p=p2p, django=task["family"] == "django", sympy=False,
        timeout=float(task.get("grader_timeout_seconds", 600)),
    )
    empty_counts = counts(empty, f2p, p2p)
    gold_counts = counts(gold, f2p, p2p)
    changed = empty_counts["outcomes"] != gold_counts["outcomes"]
    gold_f2p_ok = gold_counts["f2p_total"] > 0 and gold_counts["f2p_passed"] == gold_counts["f2p_total"]
    empty_f2p_fails = empty_counts["f2p_passed"] < empty_counts["f2p_total"]
    p2p_excluded = [node for node in p2p if gold_counts["outcomes"].get(node) != "passed"]
    accepted = bool(clean.get("answer_isolation_pass") and empty_f2p_fails and gold_f2p_ok and changed)
    row = {
        "task_id": task["id"],
        "accepted": accepted,
        "reason": None if accepted else ("delta_has_no_effect" if not changed else "calibration_failed"),
        "empty_f2p": [empty_counts["f2p_passed"], empty_counts["f2p_total"]],
        "gold_f2p": [gold_counts["f2p_passed"], gold_counts["f2p_total"]],
        "empty_p2p": [empty_counts["p2p_passed"], empty_counts["p2p_total"]],
        "gold_p2p": [gold_counts["p2p_passed"], gold_counts["p2p_total"]],
        "p2p_excluded_count": len(p2p_excluded),
        "sklearn_import": sklearn_import(image) if task["family"] == "scikit-learn" else None,
    }
    if task["family"] == "scikit-learn" and not row["sklearn_import"]:
        row["accepted"] = False
        row["reason"] = "sklearn_import_failed"
    if task["id"] in {"django__django-11039", "sympy__sympy-11400", "scikit-learn__scikit-learn-10297"}:
        from src.execution.baseline_image_backend import BaselineImageBackend
        backend = BaselineImageBackend(
            image=image, context="desktop-linux", memory_bytes=1024**3,
            workspace_bytes=256 * 1024**2, tmpfs_bytes=64 * 1024**2, network="none",
        )
        await backend.start({})
        delta = await backend.export_delta()
        await backend.close()
        row["empty_delta"] = not (delta.get("changed") or delta.get("deleted"))
        if not row["empty_delta"]:
            row["accepted"] = False
            row["reason"] = "empty_delta_not_empty"
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / (task["id"] + ".json")).write_text(json.dumps(row, indent=2) + "\n", encoding="utf-8")
    print(task["id"], row["accepted"], row["reason"], row["empty_f2p"], row["gold_f2p"], flush=True)
    return row


async def main():
    tasks = yaml.safe_load((ROOT / "configs/sprint/dev-tasks.yaml").read_text(encoding="utf-8"))["tasks"]
    wanted = sys.argv[1:]
    if wanted:
        tasks = [task for task in tasks if task["id"] in wanted]
    for task in tasks:
        if (OUT / (task["id"] + ".json")).exists() and "--rebuild" not in sys.argv:
            print(task["id"], "skip", flush=True)
            continue
        await one(task)


if __name__ == "__main__":
    asyncio.run(main())
