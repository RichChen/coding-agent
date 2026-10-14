"""Re-grade the 11 memory-source deltas with the image grader. No model calls."""
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.sprint2_calibrate import candidates, spec_ids
from src.eval.image_grader import ImageGrader


def as_delta(raw: dict) -> dict:
    changed = {}
    for name, item in (raw.get("changed") or {}).items():
        if isinstance(item, dict):
            changed[name] = item.get("content") or ""
        else:
            changed[name] = item
    return {"changed": changed, "deleted": list(raw.get("deleted") or [])}


async def main():
    snapshot = ROOT / "docs/upgrade/evidence/A5-real240-77-harness-preflight/memory-snapshot.jsonl"
    calibrated = {
        json.loads(line)["id"]: json.loads(line)
        for line in (ROOT / "runs/sprint2-calibrate/results.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    trees = candidates()
    rows = []
    for line in snapshot.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        source_id = record["source_id"]
        task_dir = trees.get(source_id)
        calibration = calibrated.get(source_id)
        if task_dir is None or calibration is None or not calibration.get("accepted"):
            reason = "gold calibration did not pass" if calibration and not calibration.get("accepted") else "no calibrated baseline"
            rows.append({"source_id": source_id, "status": "grader_unavailable", "f2p_passed": 0, "f2p_total": 0, "p2p_passed": 0, "p2p_total": 0, "reason": reason, "calibrated": False})
            print(json.dumps(rows[-1]), flush=True)
            continue
        receipt, family, f2p, p2p, overlay = spec_ids(task_dir)
        excluded = set(calibration.get("p2p_excluded") or [])
        p2p = [node for node in p2p if node not in excluded]
        delta_path = Path(record["source_dir"]) / "candidate-delta.json"
        if not delta_path.is_file():
            rows.append({"source_id": source_id, "status": "grader_unavailable", "f2p_passed": 0, "f2p_total": len(f2p), "p2p_passed": 0, "p2p_total": len(p2p), "reason": "candidate delta missing", "calibrated": True})
            print(json.dumps(rows[-1]), flush=True)
            continue
        result = await ImageGrader().evaluate(
            image=receipt["baseline_image_digest"],
            delta=as_delta(json.loads(delta_path.read_text(encoding="utf-8"))),
            test_overlay=overlay, f2p=f2p, p2p=p2p, django=family == "django", timeout=600,
        )
        if result.get("reason") and result.get("f2p_total") in (None, 0):
            label = "grader_unavailable"
        elif result.get("solved"):
            label = "pass"
        elif result.get("f2p_passed"):
            label = "partial"
        else:
            label = "fail"
        rows.append({
            "source_id": source_id, "status": label,
            "f2p_passed": result.get("f2p_passed") or 0, "f2p_total": result.get("f2p_total") or 0,
            "p2p_passed": result.get("p2p_passed") or 0, "p2p_total": result.get("p2p_total") or 0,
            "reason": result.get("reason"), "calibrated": True,
        })
        print(json.dumps(rows[-1]), flush=True)
    destination = ROOT / "docs/sprint/memory-source-verification.json"
    destination.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
