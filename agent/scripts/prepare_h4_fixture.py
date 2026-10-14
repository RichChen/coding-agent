"""Prepare one public/private H4 handoff bundle without running any model."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reposkill_agent.eval.h4_fixture import prepare_h4_fixture  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--image", required=True, help="Digest-pinned grader image; not pulled")
    args = parser.parse_args()
    print(json.dumps(prepare_h4_fixture(args.output, image=args.image), indent=2))


if __name__ == "__main__":
    main()
