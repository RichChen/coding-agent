"""Apply the missing_regrade rule to a finished run: grade its image again with an empty delta. No model calls.

When the regrade has no missing id and matches calibration, the run becomes an ordinary failure: summary.json
gets grader_candidate_error="execution" and missing_regrade, and the old summary is kept as
summary.pre-regrade.json. Otherwise nothing in the run changes.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.run_a5_main import accepted_tasks, load_targets, materialize_runner_task  # noqa: E402
from scripts.run_swe_task import calibration_row, delta_changes, empty_regrade, prerun_check  # noqa: E402
from src.eval.candidate_error import classify_missing, expected_empty, missing_count, regrade_verdict  # noqa: E402


async def regrade_run(run_dir: Path) -> dict:
    summary_path = run_dir / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    evaluation = json.loads((run_dir / "grader-result.json").read_text(encoding="utf-8"))
    if not missing_count(evaluation):
        raise SystemExit("the grader reported no missing id for " + str(run_dir))
    if summary.get("grader_candidate_error"):
        raise SystemExit("already classified: " + str(run_dir))
    task = next(task for task in accepted_tasks(load_targets()) if task["id"] == summary["task_id"])
    prepared = materialize_runner_task(task)
    spec, image, clean, failure = prerun_check(prepared, mock=False)
    if failure:
        raise SystemExit("pre-run check failed: " + failure)
    if clean is not None and summary.get("clean_image_digest") not in (None, image):
        raise SystemExit("image differs from the run: " + str(image) + " vs " + str(summary.get("clean_image_digest")))
    f2p = [node for node in spec.expected_nodeids if node not in spec.baseline_passed]
    regrade = await empty_regrade(prepared, image, spec, f2p)
    (run_dir / "grader-regrade-empty.json").write_text(json.dumps(regrade, indent=2, default=str), encoding="utf-8")
    verdict = regrade_verdict(regrade, expected_empty(calibration_row(prepared["id"])))
    delta_path = run_dir / "candidate-delta.json"
    changed = delta_changes(json.loads(delta_path.read_text(encoding="utf-8"))) if delta_path.is_file() else []
    error = classify_missing(evaluation, changed, verdict)
    result = {"run": str(run_dir.relative_to(ROOT).as_posix()), "image": image, "missing_regrade": verdict, "grader_candidate_error": error}
    if error is not None:
        (run_dir / "summary.pre-regrade.json").write_text(summary_path.read_text(encoding="utf-8"), encoding="utf-8")
        summary["grader_candidate_error"] = error
        summary["missing_regrade"] = verdict
        summary["solved"] = False
        summary["docker_retries"] = list(summary.get("docker_retries") or []) + [
            dict(stage="regrade", **row) for row in regrade.get("docker_retries") or []]
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir")
    args = parser.parse_args()
    run_dir = Path(args.run_dir)
    if not run_dir.is_absolute():
        run_dir = ROOT / run_dir
    result = asyncio.run(regrade_run(run_dir))
    print(json.dumps(result, indent=2))
    if result["grader_candidate_error"] is None:
        raise SystemExit("the empty regrade does not clear this run; the stop stands")


if __name__ == "__main__":
    main()
