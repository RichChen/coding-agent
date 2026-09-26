"""Select the A5-main pool from SWE-bench Verified. No model calls."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REPOS = (
    "django/django",
    "sympy/sympy",
    "scikit-learn/scikit-learn",
    "sphinx-doc/sphinx",
    "pytest-dev/pytest",
)
PER_REPO = 12


def even_indexes(count: int, take: int) -> list[int]:
    """Stable even sample, oldest to newest, no duplicates."""
    if count <= take:
        return list(range(count))
    return [int(i * count / take) for i in range(take)]


def select(rows: list[dict], excluded: set[str]) -> list[dict]:
    chosen = []
    for repo in REPOS:
        pool = [row for row in rows if row["repo"] == repo and row["instance_id"] not in excluded]
        pool.sort(key=lambda row: (str(row["created_at"]), row["instance_id"]))
        for index in even_indexes(len(pool), PER_REPO):
            chosen.append(pool[index])
    return chosen


def main():
    from datasets import load_dataset

    excluded = {task["id"] for task in yaml.safe_load((ROOT / "configs/sprint/dev-tasks.yaml").read_text(encoding="utf-8"))["tasks"]}
    dataset = load_dataset("princeton-nlp/SWE-bench_Verified", split="test")
    rows = [dict(row) for row in dataset]
    picked = select(rows, excluded)
    private_root = ROOT / "runs" / "sprint5-main-private"
    private_root.mkdir(parents=True, exist_ok=True)
    tasks = []
    for row in picked:
        private = {
            "instance_id": row["instance_id"],
            "FAIL_TO_PASS": row["FAIL_TO_PASS"],
            "PASS_TO_PASS": row["PASS_TO_PASS"],
            "patch": row["patch"],
            "test_patch": row["test_patch"],
        }
        path = private_root / (row["instance_id"] + ".json")
        path.write_text(json.dumps(private, ensure_ascii=False) + "\n", encoding="utf-8")
        tasks.append({
            "id": row["instance_id"],
            "repo": row["repo"],
            "created_at": str(row["created_at"]),
            "base_commit": row["base_commit"],
            "version": str(row.get("version") or ""),
            "image_source": "pending-step2",
            "private": "runs/sprint5-main-private/" + row["instance_id"] + ".json",
        })
    document = {"schema": "sprint.main-targets.v1", "tasks": tasks}
    out = ROOT / "configs" / "sprint" / "main-targets.yaml"
    out.write_text(yaml.safe_dump(document, sort_keys=False, allow_unicode=True), encoding="utf-8")
    ids = "\n".join(task["id"] for task in tasks) + "\n"
    print(len(tasks))
    print(hashlib.sha256(ids.encode()).hexdigest())


if __name__ == "__main__":
    main()
