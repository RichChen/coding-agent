#!/usr/bin/env python3
"""Run Batch 4.5 mechanism smoke checks (Phase7 skill/memory/context/repair)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/test_mechanism_smoke.py",
        "-q",
    ]
    print("Running mechanism smoke tests...")
    proc = subprocess.run(cmd, cwd=ROOT, check=False)
    if proc.returncode == 0:
        print("Mechanism smoke: PASS")
    else:
        print("Mechanism smoke: FAIL", file=sys.stderr)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
