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
DATASET = "princeton-nlp/SWE-bench_Verified"
PUBLIC_ROOT = ROOT / "runs" / "sprint5-main-public"
ISSUES = ROOT / "docs" / "sprint" / "main-issues.json"


def issue_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def ids_sha256(ids) -> str:
    return hashlib.sha256(("\n".join(ids) + "\n").encode()).hexdigest()


def public_record(row: dict) -> dict:
    """Agent-visible task: the issue verbatim (no strip, no hints_text) and the repo ref."""
    text = row["problem_statement"]
    if not isinstance(text, str) or not text:
        raise ValueError("empty problem_statement for " + row["instance_id"])
    return {
        "task_id": row["instance_id"],
        "issue_text": text,
        "issue_sha256": issue_sha256(text),
        "repo_ref": {"repo_id": row["repo"], "revision": row["base_commit"], "revision_kind": "commit"},
    }


def write_public(rows: list[dict], dataset: dict) -> dict:
    """Write runs/sprint5-main-public/<id>.json and docs/sprint/main-issues.json."""
    PUBLIC_ROOT.mkdir(parents=True, exist_ok=True)
    issues = {}
    for row in rows:
        record = public_record(row)
        path = PUBLIC_ROOT / (row["instance_id"] + ".json")
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        issues[row["instance_id"]] = {"issue_sha256": record["issue_sha256"], "chars": len(record["issue_text"])}
    document = {
        "schema": "sprint.main-issues.v1",
        "dataset": dataset,
        "ids_sha256": ids_sha256(row["instance_id"] for row in rows),
        "tasks": issues,
    }
    ISSUES.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return document


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
    dataset = load_dataset(DATASET, split="test")
    rows = [dict(row) for row in dataset]
    picked = select(rows, excluded)
    write_public(picked, {"name": DATASET, "split": "test", "fingerprint": dataset._fingerprint})
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
    print(len(tasks))
    print(ids_sha256(task["id"] for task in tasks))


if __name__ == "__main__":
    main()
