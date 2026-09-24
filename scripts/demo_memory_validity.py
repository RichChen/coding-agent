"""Run the synthetic offline upgrade walkthrough, without an API key."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from reposkill_agent.eval.upgrade_demo import run_demo  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New output directory.")
    args = parser.parse_args()
    result = run_demo(args.output)
    print(f"Offline demo: {len(result['drift_matrix'])} comparisons; model calls=0")
    print(args.output / "report.md")


if __name__ == "__main__":
    main()
