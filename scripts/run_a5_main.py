"""Run the main-pool comparison. All B0 repeats finish before any B2 repeat starts."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from decimal import Decimal
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.handoff_sha import handoff_sha256  # noqa: E402
from scripts.preflight_a5_repo_baseline import patch_paths  # noqa: E402
from scripts.run_swe_task import run_task  # noqa: E402
from scripts.sprint5_prepare_main import FAMILY  # noqa: E402

TOTAL_CAP = Decimal("150")
PARALLEL = 3


def load_targets():
    return yaml.safe_load((ROOT / "configs/sprint/main-targets.yaml").read_text(encoding="utf-8"))["tasks"]


def accepted_tasks(tasks):
    folder = ROOT / "docs" / "sprint" / "main-calibration"
    kept = []
    for task in tasks:
        path = folder / (task["id"] + ".json")
        if not path.is_file():
            continue
        row = json.loads(path.read_text(encoding="utf-8"))
        if row.get("accepted"):
            kept.append(task)
    return kept


def spent(root: Path) -> Decimal:
    total = Decimal("0")
    if not root.exists():
        return total
    for path in root.rglob("summary.json"):
        row = json.loads(path.read_text(encoding="utf-8"))
        total += Decimal(str(row.get("cost_cny") or "0"))
    return total


async def run_phase(tasks, phase: str, *, cards: Path | None, mock: bool, repeats: int):
    out_root = ROOT / "runs" / "a5-main"
    profile = ROOT / "configs/sprint/b0-v2.yaml"
    variant = "B0" if phase == "b0" else "B2"
    pending = []
    for task in tasks:
        for repeat in range(1, repeats + 1):
            output = out_root / task["id"] / phase / ("r" + str(repeat))
            if (output / "summary.json").is_file():
                continue
            pending.append((task, output))
    if spent(out_root) >= TOTAL_CAP:
        raise SystemExit("CNY total cap reached before this phase")
    semaphore = asyncio.Semaphore(PARALLEL)

    async def one(task, output):
        if spent(out_root) >= TOTAL_CAP:
            return None
        async with semaphore:
            if spent(out_root) >= TOTAL_CAP:
                return None
            output.mkdir(parents=True, exist_ok=True)
            return await run_task(
                materialize_runner_task(task), profile, output, mock=mock, variant=variant, cards_path=cards,
            )

    results = await asyncio.gather(*(one(task, output) for task, output in pending))
    return [item for item in results if item is not None]


def materialize_runner_task(task: dict) -> dict:
    """Give a pool task the receipt and public issue run_task already expects.

    Generated files stay under runs/. The public file does not contain patches.
    """
    if task.get("receipt") and task.get("public_task") and task.get("family"):
        return task
    private_path = ROOT / task["private"]
    private = json.loads(private_path.read_text(encoding="utf-8"))
    clean = json.loads((ROOT / "docs" / "sprint" / "clean-images" / (task["id"] + ".json")).read_text(encoding="utf-8"))
    calibration_path = ROOT / "docs" / "sprint" / "main-calibration" / (task["id"] + ".json")
    excluded = []
    if calibration_path.is_file():
        excluded = json.loads(calibration_path.read_text(encoding="utf-8")).get("p2p_excluded") or []
    folder = ROOT / "runs" / "sprint5-main-runner" / task["id"]
    folder.mkdir(parents=True, exist_ok=True)
    archive = ROOT / "runs" / "sprint5-main-images" / task["id"] / "source.tar.gz"
    receipt = {
        "baseline_image_digest": clean["clean_image_digest"],
        "base_revision": task["base_commit"],
        "source_attempt_ref": archive.as_posix(),
        "private_source_binding": {
            "path": private_path.as_posix(),
            "test_patch_paths": patch_paths(private.get("test_patch") or ""),
            "gold_patch_paths": patch_paths(private.get("patch") or ""),
        },
    }
    receipt_path = folder / "receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    public = {
        "issue_text": private.get("problem_statement") or ("Public issue for " + task["id"]),
        "repo_ref": {"repo_id": task["repo"], "revision": task["base_commit"]},
    }
    public_path = folder / "public-task.json"
    public_path.write_text(json.dumps(public, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    staging = ROOT / "runs" / "sprint5-main-images" / task["id"] / "staging"
    prepared = dict(task)
    prepared["family"] = FAMILY[task["repo"]]
    prepared["receipt"] = receipt_path.relative_to(ROOT).as_posix()
    prepared["public_task"] = public_path.as_posix()
    prepared["original"] = (staging / "original").relative_to(ROOT).as_posix()
    prepared["baseline"] = (staging / "baseline").relative_to(ROOT).as_posix()
    prepared["grader_timeout_seconds"] = 600
    prepared["p2p_excluded"] = excluded
    return prepared


def write_b0_handoff(*, mock: bool = False):
    out_root = ROOT / "runs" / "a5-main"
    runs = []
    for task in accepted_tasks(load_targets()):
        for repeat in (1, 2, 3):
            summary_path = out_root / task["id"] / "b0" / ("r" + str(repeat)) / "summary.json"
            if not summary_path.is_file():
                continue
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            runs.append({
                "source_id": task["id"],
                "repo": task["repo"],
                "created_at": task["created_at"],
                "repeat": repeat,
                "solved": summary.get("solved"),
                "status": summary.get("status"),
                "cost_cny": summary.get("cost_cny"),
                "summary": str(summary_path.relative_to(ROOT)).replace("\\", "/"),
            })
    destination = ROOT / "docs" / "sprint" / "main-b0-runs.json"
    payload = {
        "schema": "sprint6.main-b0-runs.v1",
        "profile_tag": "b0-v2",
        "runs": runs,
    }
    if mock:
        payload["scope"] = "step7-mock"
        payload["note"] = "Zero-model walk of three accepted tasks. This is not the R6 handoff."
    destination.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(handoff_sha256(destination), flush=True)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=["b0", "b2"], required=True)
    parser.add_argument("--cards", default=None)
    parser.add_argument("--mock", action="store_true")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--task", action="append", default=[])
    args = parser.parse_args()
    if args.phase == "b2" and not args.cards:
        raise SystemExit("B2 requires --cards")
    tasks = accepted_tasks(load_targets())
    if args.task:
        wanted = set(args.task)
        tasks = [task for task in tasks if task["id"] in wanted]
        missing = wanted - {task["id"] for task in tasks}
        if missing:
            raise SystemExit("not an accepted task: " + ", ".join(sorted(missing)))
    if not tasks:
        raise SystemExit("no accepted main-pool tasks")
    cards = Path(args.cards) if args.cards else None
    if cards is not None and not cards.is_absolute():
        cards = ROOT / cards
    asyncio.run(run_phase(tasks, args.phase, cards=cards, mock=args.mock, repeats=args.repeats))
    if args.phase == "b0":
        write_b0_handoff(mock=args.mock)
        print("B0 finished. Stop for card building.", flush=True)


if __name__ == "__main__":
    main()
