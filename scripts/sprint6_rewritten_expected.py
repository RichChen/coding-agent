"""Record the expected sha of every pre_install-rewritten file and check each clean image against it. No model calls."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_clean_baseline import source_only_check  # noqa: E402
from scripts.rewritten_sources import overrides_for, sed_rewrites, write_expected  # noqa: E402
from scripts.run_a5_main import accepted_tasks, load_targets  # noqa: E402
from scripts.swebench_specs import spec_row  # noqa: E402
from src.eval.a5_image_tree import archive_manifest  # noqa: E402


def main():
    failed = []
    for task in accepted_tasks(load_targets()):
        spec = spec_row(task["repo"], task["version"])
        if not sed_rewrites(spec):
            continue
        clean = json.loads((ROOT / "docs" / "sprint" / "clean-images" / (task["id"] + ".json")).read_text(encoding="utf-8"))
        archive = ROOT / "runs" / "sprint5-main-images" / task["id"] / "source.tar.gz"
        manifest = archive_manifest(archive, task["repo"], task["base_commit"])
        path = write_expected(task, spec, clean["clean_image_digest"], archive)
        overrides = overrides_for(task, manifest)
        matched, result = source_only_check(clean["clean_image_digest"], manifest, overrides)
        row = json.loads(path.read_text(encoding="utf-8"))
        changed = sum(1 for item in row["files"].values() if item["original_sha256"] != item["expected_sha256"])
        print(task["id"], "files", len(overrides), "changed by sed", changed, "match", matched, result, flush=True)
        if not matched:
            failed.append(task["id"])
    if failed:
        raise SystemExit("images do not match the replayed files: " + ", ".join(failed))


if __name__ == "__main__":
    main()
