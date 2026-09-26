"""Scan one SWE-bench official image for test-patch and gold lines. No model calls."""
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_clean_baseline import filesystem_scan  # noqa: E402
from src.eval.a5_image_tree import archive_manifest  # noqa: E402


def main():
    task_id = sys.argv[1]
    image = sys.argv[2]
    tasks = yaml.safe_load((ROOT / "configs/sprint/dev-tasks.yaml").read_text(encoding="utf-8"))["tasks"]
    task = next(item for item in tasks if item["id"] == task_id)
    receipt = json.loads((ROOT / task["receipt"]).read_text(encoding="utf-8"))
    private = json.loads(Path(receipt["private_source_binding"]["path"]).read_text(encoding="utf-8"))
    archive = Path(receipt["source_attempt_ref"]).parent / "source.tar.gz"
    manifest = archive_manifest(archive, task["repo"], receipt["base_revision"])
    scan = filesystem_scan(
        image, archive, manifest, private.get("test_patch") or "", private.get("patch") or "",
        python_bin="/opt/miniconda3/envs/testbed/bin/python",
    )
    print(json.dumps({
        "task_id": task_id,
        "base_revision": receipt["base_revision"],
        "needle_count": scan.get("needle_count"),
        "hits": len(scan.get("hits") or []),
        "pass": scan.get("pass"),
    }))


if __name__ == "__main__":
    main()
