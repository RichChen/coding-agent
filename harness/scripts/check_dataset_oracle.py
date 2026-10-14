#!/usr/bin/env python3
"""Validate dataset oracle solutions against expected judges (CI-only, not fed to Agent)."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.eval.runner import EvalRunner
from src.runtime.loop import AgentRunResult


def _apply_oracle(workspace: Path, fixture_dir: Path) -> str | None:
    oracle_dir = fixture_dir / ".oracle"
    if not oracle_dir.exists():
        return None
    for item in oracle_dir.iterdir():
        if item.is_dir():
            shutil.copytree(item, workspace / item.name, dirs_exist_ok=True)
        else:
            shutil.copy2(item, workspace / item.name)
    answer_file = oracle_dir / "final_answer.txt"
    if answer_file.exists():
        return answer_file.read_text(encoding="utf-8").strip()
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate dataset oracle solutions")
    parser.add_argument(
        "--dataset",
        default="datasets/repo_tasks.json",
        help="Dataset JSON path (default: datasets/repo_tasks.json)",
    )
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    with open(dataset_path, encoding="utf-8") as f:
        data = json.load(f)
    tasks = data["tasks"] if isinstance(data, dict) else data

    failures: list[str] = []
    checked = 0

    for task in tasks:
        fixture_dir = task.get("fixture_dir")
        if not fixture_dir:
            continue
        fixture = Path(fixture_dir)
        if not (fixture / ".oracle").exists():
            continue

        with tempfile.TemporaryDirectory(prefix="oracle_") as tmp:
            workspace = Path(tmp)
            EvalRunner._copy_fixture_dir(workspace, fixture)
            final_answer = _apply_oracle(workspace, fixture)
            result = AgentRunResult(
                task_id=task["id"],
                success=True,
                final_answer=final_answer,
            )
            ok, reasons = EvalRunner._explain_expected(
                workspace, result, task.get("expected", {})
            )
            checked += 1
            if not ok:
                failures.append(f"{task['id']}: {'; '.join(reasons)}")

    print(f"Checked {checked} oracle task(s).")
    if failures:
        print("Oracle validation FAILED:")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("All oracle solutions PASS.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
