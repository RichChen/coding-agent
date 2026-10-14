#!/usr/bin/env python3
"""Export a cold validated_lightweight memory snapshot. No model or pilot."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.eval.a5_memory_snapshot import export_snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = export_snapshot(input_path=args.input.resolve(), output_dir=args.output_dir)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("boundary_passed") else 2


if __name__ == "__main__":
    raise SystemExit(main())
