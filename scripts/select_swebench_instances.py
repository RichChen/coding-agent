#!/usr/bin/env python3
"""Select SWE-bench Lite candidates from target repos.

Prints concise candidate rows for manual/agent feasibility validation.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime

from datasets import load_dataset


def _parse_created_at(value: str) -> datetime:
    # Dataset uses ISO-8601 UTC timestamps (e.g. 2023-08-10T20:14:55Z)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Select SWE-bench Lite candidates")
    parser.add_argument(
        "--repos",
        nargs="+",
        default=["pallets/flask", "psf/requests", "sympy/sympy"],
        help="Target repos to include",
    )
    parser.add_argument(
        "--split",
        default="test",
        help="Dataset split (default: test)",
    )
    parser.add_argument(
        "--limit-per-repo",
        type=int,
        default=6,
        help="How many newest candidates to print per repo",
    )
    parser.add_argument(
        "--problem-preview-chars",
        type=int,
        default=200,
        help="Preview length for problem statement",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional output jsonl file path (UTF-8)",
    )
    args = parser.parse_args()

    ds = load_dataset("princeton-nlp/SWE-bench_Lite", split=args.split)

    selected: list[dict] = []
    for repo in args.repos:
        rows = [row for row in ds if row["repo"] == repo]
        rows.sort(key=lambda r: _parse_created_at(r["created_at"]), reverse=True)
        selected.extend(rows[: max(0, args.limit_per_repo)])

    selected.sort(key=lambda r: _parse_created_at(r["created_at"]), reverse=True)

    lines = [
        json.dumps(
            {
                "dataset": "princeton-nlp/SWE-bench_Lite",
                "split": args.split,
                "target_repos": args.repos,
                "candidate_count": len(selected),
            },
            ensure_ascii=False,
        )
    ]

    for idx, row in enumerate(selected, start=1):
        fail_to_pass = json.loads(row["FAIL_TO_PASS"])
        pass_to_pass = json.loads(row["PASS_TO_PASS"])
        preview = row["problem_statement"].replace("\n", " ").strip()
        preview = preview[: args.problem_preview_chars]
        lines.append(
            json.dumps(
                {
                    "index": idx,
                    "instance_id": row["instance_id"],
                    "repo": row["repo"],
                    "base_commit": row["base_commit"],
                    "version": row["version"],
                    "created_at": row["created_at"],
                    "fail_to_pass_count": len(fail_to_pass),
                    "pass_to_pass_count": len(pass_to_pass),
                    "FAIL_TO_PASS": fail_to_pass,
                    "PASS_TO_PASS": pass_to_pass[:20],
                    "problem_statement_preview": preview,
                },
                ensure_ascii=False,
            )
        )

    for line in lines:
        print(line)
    if args.output:
        from pathlib import Path

        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
