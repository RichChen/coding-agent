"""Diagnose a grader stop without model calls: grade the run's image with an empty delta, then with the
run's own candidate delta again. Writes diagnostic-grader-rerun.json into the run directory and changes
nothing else.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.run_a5_main import accepted_tasks, load_targets, materialize_runner_task  # noqa: E402
from scripts.run_swe_task import calibration_row, empty_regrade, prerun_check  # noqa: E402
from src.eval.candidate_error import expected_empty, regrade_verdict  # noqa: E402
from src.eval.image_grader import ImageGrader  # noqa: E402


async def diagnose(run_dir: Path) -> dict:
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    task = next(t for t in accepted_tasks(load_targets()) if t["id"] == summary["task_id"])
    prepared = materialize_runner_task(task)
    spec, image, clean, failure = prerun_check(prepared, mock=False)
    if failure:
        raise SystemExit("pre-run check failed: " + failure)
    f2p = [n for n in spec.expected_nodeids if n not in spec.baseline_passed]
    started = time.monotonic()
    empty = await empty_regrade(prepared, image, spec, f2p)
    empty_s = round(time.monotonic() - started, 1)
    delta = json.loads((run_dir / "candidate-delta.json").read_text(encoding="utf-8"))
    started = time.monotonic()
    again = await ImageGrader().evaluate(
        image=image, delta=delta, test_overlay=spec.test_overlay, f2p=f2p, p2p=list(spec.baseline_passed),
        django=prepared.get("family") == "django", sympy=False, timeout=float(prepared["grader_timeout_seconds"]),
    )
    again_s = round(time.monotonic() - started, 1)
    out = {
        "image": image,
        "summary_image": summary.get("clean_image_digest"),
        "empty": {"seconds": empty_s, "execution_status": empty.get("execution_status"),
                  "verdict": regrade_verdict(empty, expected_empty(calibration_row(prepared["id"])))},
        "candidate_again": {
            "seconds": again_s,
            "status": again.get("status"),
            "execution_status": again.get("execution_status"),
            "reason": (again.get("reason") or "")[:300],
            "f2p": [again.get("f2p_passed"), again.get("f2p_total")],
            "p2p": [again.get("p2p_passed"), again.get("p2p_total")],
            "stderr_tail": (again.get("execution_stderr_tail") or "")[-1500:],
        },
    }
    (run_dir / "diagnostic-grader-rerun.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir")
    args = parser.parse_args()
    run_dir = Path(args.run_dir)
    if not run_dir.is_absolute():
        run_dir = ROOT / run_dir
    print(json.dumps(asyncio.run(diagnose(run_dir)), indent=2))


if __name__ == "__main__":
    main()
