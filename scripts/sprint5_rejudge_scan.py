"""Re-judge stored main-pool scan receipts under the exclusion guard. No image rebuild, no model."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_clean_baseline import exclusion_guarded, repo_packages  # noqa: E402
from src.eval.a5_image_tree import archive_manifest  # noqa: E402

CLEAN = ROOT / "docs" / "sprint" / "clean-images"
CAL = ROOT / "docs" / "sprint" / "main-calibration"
WORK = ROOT / "runs" / "sprint5-main-images"
LISTED = 20


def rejudge(task: dict) -> dict:
    clean = json.loads((CLEAN / (task["id"] + ".json")).read_text(encoding="utf-8"))
    scan = clean["filesystem_scan"]
    for key in ("base_image_same", "install_record_same"):
        if scan.get(key + "_count", 0) > LISTED:
            raise SystemExit(task["id"] + ": " + key + " list is truncated; rescan the image instead")
    manifest = archive_manifest(WORK / task["id"] / "source.tar.gz", task["repo"], task["base_commit"])
    packages = sorted(repo_packages(manifest))
    excused = [(path, "base_image_same") for path in scan.get("base_image_same") or []]
    excused += [(path, "install_record_same") for path in scan.get("install_record_same") or []]
    guarded = [path for path, _ in excused if exclusion_guarded(path, set(packages))]
    hits = (scan.get("hit_count") or 0) + len(guarded)
    passed = bool(clean.get("source_only_match")) and hits == 0
    return {
        "task_id": task["id"],
        "packages": packages,
        "excused": [{"path": path, "rule": rule} for path, rule in excused],
        "guarded": guarded,
        "hit_count": hits,
        "answer_isolation_pass": passed,
        "unchanged": passed == bool(clean.get("answer_isolation_pass")),
    }


def main() -> None:
    tasks = yaml.safe_load((ROOT / "configs/sprint/main-targets.yaml").read_text(encoding="utf-8"))["tasks"]
    rows = []
    for task in tasks:
        calibration = CAL / (task["id"] + ".json")
        if not calibration.is_file() or not json.loads(calibration.read_text(encoding="utf-8")).get("accepted"):
            continue
        rows.append(rejudge(task))
    changed = [row["task_id"] for row in rows if not row["unchanged"]]
    report = {
        "receipts": len(rows),
        "excused_files": sum(len(row["excused"]) for row in rows),
        "guarded_files": sum(len(row["guarded"]) for row in rows),
        "verdict_changed": changed,
        "rows": rows,
    }
    destination = ROOT / "docs" / "sprint" / "scan-rejudge.json"
    destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "rows"}))


if __name__ == "__main__":
    main()
