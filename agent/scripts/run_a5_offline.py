"""Run A5 deterministic plumbing fixtures only; there is no real-API switch."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reposkill_agent.experiments.offline import run_offline  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = run_offline(args.output)
    print(
        json.dumps(
            {
                "smoke_scenarios": result["smoke_scenarios"],
                "decisions": result["decision_rows"],
                "external_model_calls": result["external_model_calls"],
                "main_assigned": 0,
                "output": str(args.output),
            }
        )
    )


if __name__ == "__main__":
    main()
