#!/usr/bin/env python3
"""Recompute hashes and public/private boundary for a memory snapshot."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.eval.a5_memory_snapshot import audit_snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    try:
        result = audit_snapshot(
            snapshot_path=args.snapshot.resolve(),
            manifest_path=args.manifest.resolve(),
            output_path=args.output.resolve() if args.output else None,
        )
    except ValueError as exc:
        print(str(exc))
        return 2
    print(json.dumps({"status": result["status"], "snapshot_hash": result["snapshot_hash"],
                      "model_calls": 0, "paid": False}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
