"""Restore the public issue text for the already-selected A5-main pool. No re-selection, no model calls.

Reads SWE-bench Verified test at a pinned Hub revision, reproduces the selection, refuses to write
anything unless the 60 ids (and their order) are unchanged, then writes the public files.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.select_main_targets import DATASET, ids_sha256, select, write_public  # noqa: E402

REVISION = "c104f840cc67f8b6eec6f759ebc8b2693d585d4a"
FILENAME = "data/test-00000-of-00001.parquet"
IDS_SHA256 = "d4caaa48"


def main():
    import pyarrow.parquet as pq
    from huggingface_hub import hf_hub_download

    path = hf_hub_download(DATASET, FILENAME, repo_type="dataset", revision=REVISION)
    file_sha = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    rows = pq.read_table(path).to_pylist()
    targets = yaml.safe_load((ROOT / "configs/sprint/main-targets.yaml").read_text(encoding="utf-8"))["tasks"]
    dev = yaml.safe_load((ROOT / "configs/sprint/dev-tasks.yaml").read_text(encoding="utf-8"))["tasks"]
    picked = select(rows, {task["id"] for task in dev})
    ids = [row["instance_id"] for row in picked]
    if ids != [task["id"] for task in targets]:
        raise SystemExit("reproduced selection differs from configs/sprint/main-targets.yaml")
    if not ids_sha256(ids).startswith(IDS_SHA256):
        raise SystemExit("60-id sha changed: " + ids_sha256(ids))
    for row, task in zip(picked, targets):
        if row["base_commit"] != task["base_commit"] or row["repo"] != task["repo"]:
            raise SystemExit("repo or base_commit differs for " + task["id"])
    document = write_public(picked, {
        "name": DATASET,
        "split": "test",
        "revision": REVISION,
        "file": FILENAME,
        "file_sha256": file_sha,
        "rows": len(rows),
    })
    chars = sorted(item["chars"] for item in document["tasks"].values())
    print(len(chars), document["ids_sha256"], "chars min/median/max", chars[0], chars[len(chars) // 2], chars[-1])


if __name__ == "__main__":
    main()
