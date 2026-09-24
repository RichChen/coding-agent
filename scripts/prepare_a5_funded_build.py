"""Prepare authorized build jobs, without starting any model or host runtime."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reposkill_agent.experiments.funding import prepare_funded_build  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--funding", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare_funded_build(args.bundle, args.funding, args.output)))


if __name__ == "__main__":
    main()
