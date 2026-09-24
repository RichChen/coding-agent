#!/usr/bin/env python3
"""Lock the 240 matrix, receipt schema, and pilot budget. Never starts a paid run."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.eval.a5_pilot_lock import lock_pilot


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = lock_pilot(output_dir=args.output_dir)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["matrix_lock_status"] == "matrix_locked" else 2


if __name__ == "__main__":
    raise SystemExit(main())
