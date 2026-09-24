"""Prepare pinned pilot candidates offline. No API, model or execution flag exists."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reposkill_agent.experiments.preparation import prepare_pilot20  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--lock", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = prepare_pilot20(args.source, args.lock, args.output)
    print(
        json.dumps(
            {
                key: result[key]
                for key in (
                    "target_candidates",
                    "history_candidates",
                    "planned_task_runs",
                    "started_runs",
                    "external_model_calls",
                    "qualified_runnable_tasks",
                    "missing_same_repo_history",
                )
            }
        )
    )


if __name__ == "__main__":
    main()
