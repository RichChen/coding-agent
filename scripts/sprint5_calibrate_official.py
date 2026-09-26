"""Zero-model calibration of three official SWE-bench images."""
import asyncio
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.calibrate_clean_image import counts, gold_delta  # noqa: E402
from scripts.run_swe_task import grader_spec  # noqa: E402
from src.eval.image_grader import ImageGrader  # noqa: E402

IMAGES = {
    "django__django-10914": "swebench/sweb.eval.x86_64.django_1776_django-10914@sha256:f26f0db931c6c1e785ab8287e1ea4f5f948846267db159deaf90b3fe7adea4e9",
    "sympy__sympy-11400": "swebench/sweb.eval.x86_64.sympy_1776_sympy-11400@sha256:a9127c8893792545a1534e34773cbe1049ec2e39dbb5d7808bb1ceff76b84273",
    "scikit-learn__scikit-learn-10297": "swebench/sweb.eval.x86_64.scikit-learn_1776_scikit-learn-10297@sha256:58b80e9100f9d107291b5ea37c76583ed4851d8e18ec07aef197f1803a290986",
}
PYTHON = "/opt/miniconda3/envs/testbed/bin/python"


async def one(task):
    spec = grader_spec(task)
    f2p = [node for node in spec.expected_nodeids if node not in spec.baseline_passed]
    p2p = list(spec.baseline_passed)
    image = IMAGES[task["id"]]
    grader = ImageGrader()
    kwargs = dict(
        image=image, test_overlay=spec.test_overlay, f2p=f2p, p2p=p2p,
        django=task["family"] == "django", sympy=False,
        timeout=float(task.get("grader_timeout_seconds", 600)),
        repo_root="/testbed", python_bin=PYTHON,
    )
    empty = await grader.evaluate(delta={"changed": {}, "deleted": []}, **kwargs)
    gold = await grader.evaluate(delta=gold_delta(task, spec.test_paths), **kwargs)
    empty_counts = counts(empty, f2p, p2p)
    gold_counts = counts(gold, f2p, p2p)
    changed = empty_counts["outcomes"] != gold_counts["outcomes"]
    accepted = (
        empty_counts["f2p_passed"] < empty_counts["f2p_total"]
        and gold_counts["f2p_total"] > 0
        and gold_counts["f2p_passed"] == gold_counts["f2p_total"]
        and changed
    )
    row = {
        "task_id": task["id"],
        "accepted": accepted,
        "empty_f2p": [empty_counts["f2p_passed"], empty_counts["f2p_total"]],
        "gold_f2p": [gold_counts["f2p_passed"], gold_counts["f2p_total"]],
        "reason": None if accepted else (empty.get("reason") or gold.get("reason") or "calibration_failed"),
    }
    print(json.dumps(row), flush=True)
    return row


async def main():
    tasks = yaml.safe_load((ROOT / "configs/sprint/dev-tasks.yaml").read_text(encoding="utf-8"))["tasks"]
    wanted = set(IMAGES)
    for task in tasks:
        if task["id"] in wanted:
            await one(task)


if __name__ == "__main__":
    asyncio.run(main())
