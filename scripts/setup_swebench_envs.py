#!/usr/bin/env python3
"""Create git-ignored SWE-bench interpreter envs for portable dataset assertions."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.build_swebench_lite_subset import (  # noqa: E402
    REQUESTS_PYTHON_CMD,
    _create_python_env,
    _find_env_python,
    _install_from_specs,
    _load_swebench_py_constants,
    _run,
)

REQUESTS_INSTANCE_ID = "psf__requests-3362"
REQUESTS_ENV_DIR = Path(".swebench_envs/requests-3362")
REQUESTS_FIXTURE = Path("tests/fixtures/repos/swebench_psf__requests-3362")
LEGACY_ORACLE = Path(".tmp/swebench_oracle_py39")


def _env_python(env_dir: Path) -> Path | None:
    return _find_env_python(env_dir.resolve())


def _python_usable(py: Path) -> bool:
    proc = _run([str(py), "-c", "import requests; import pytest"], cwd=Path.cwd(), timeout=120)
    return proc.returncode == 0


def _migrate_legacy_env(target_dir: Path) -> Path | None:
    legacy_py = _find_env_python(LEGACY_ORACLE.resolve())
    if legacy_py is None or not _python_usable(legacy_py):
        return None
    if target_dir.exists():
        shutil.rmtree(target_dir, ignore_errors=True)
    shutil.copytree(LEGACY_ORACLE.resolve(), target_dir.resolve())
    py = _env_python(target_dir)
    if py and _python_usable(py):
        return py
    return None


def _build_requests_env(base_python: str, *, migrate_legacy: bool) -> Path:
    target_dir = REQUESTS_ENV_DIR.resolve()
    target_dir.parent.mkdir(parents=True, exist_ok=True)

    existing = _env_python(target_dir)
    if existing and _python_usable(existing):
        return existing

    if migrate_legacy:
        migrated = _migrate_legacy_env(target_dir)
        if migrated:
            return migrated

    if target_dir.exists():
        shutil.rmtree(target_dir, ignore_errors=True)

    py = _create_python_env(base_python, "3.9", target_dir)
    constants = _load_swebench_py_constants()
    specs = constants.map_repo_version_to_specs["psf/requests"]["2.10"]
    row = {
        "repo": "psf/requests",
        "version": "2.10",
        "base_commit": "36453b95b13079296776d11b09cab2567ea3e703",
        "environment_setup_commit": "36453b95b13079296776d11b09cab2567ea3e703",
    }
    ok, reason = _install_from_specs(py, REQUESTS_FIXTURE.resolve(), row, specs, constants)
    if not ok:
        raise RuntimeError(f"requests env install failed: {reason}")

    install = _run([str(py), "-m", "pip", "install", "-q", "."], cwd=REQUESTS_FIXTURE.resolve(), timeout=900)
    if install.returncode != 0:
        raise RuntimeError(f"requests package install failed: {install.stderr or install.stdout}")

    if not _python_usable(py):
        raise RuntimeError("requests env built but import check failed")
    return py


def main() -> int:
    parser = argparse.ArgumentParser(description="Setup git-ignored SWE-bench envs")
    parser.add_argument(
        "--python",
        default=r"C:\Users\Administrator\.conda\envs\coding-harness\python.exe",
    )
    parser.add_argument(
        "--no-migrate-legacy",
        action="store_true",
        help="Skip one-time migration from .tmp/swebench_oracle_py39 if present",
    )
    args = parser.parse_args()

    py = _build_requests_env(args.python, migrate_legacy=not args.no_migrate_legacy)
    env_var = "SWEBENCH_REQUESTS_PY"
    print(json.dumps({"env": str(REQUESTS_ENV_DIR).replace("\\", "/"), "python": str(py)}, ensure_ascii=False))
    print(f"set {env_var}={py}")
    print(f"# Dataset assertions use {REQUESTS_PYTHON_CMD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
