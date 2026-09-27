"""Read SWE-bench's per-version install specs. Do not hand-write dependency pins."""
from __future__ import annotations

import importlib.util
import sysconfig
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPECS_URL = "https://raw.githubusercontent.com/SWE-bench/SWE-bench/v4.0.4/swebench/harness/constants/python.py"
CACHE = ROOT / "runs" / "sprint5-specs" / "python.py"


def specs_path() -> Path:
    installed = (
        Path(sysconfig.get_paths()["purelib"])
        / "swebench" / "harness" / "constants" / "python.py"
    )
    if installed.is_file():
        return installed
    if not CACHE.is_file():
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(SPECS_URL, timeout=60) as response:
            CACHE.write_bytes(response.read())
    return CACHE


def load_maps():
    path = specs_path()
    spec = importlib.util.spec_from_file_location("swebench_constants_py", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load SWE-bench specs: " + str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.MAP_REPO_VERSION_TO_SPECS_PY, module.MAP_REPO_TO_REQS_PATHS


def spec_row(repo: str, version: str) -> dict:
    specs, _paths = load_maps()
    row = (specs.get(repo) or {}).get(str(version))
    if row is None:
        raise ValueError("no SWE-bench spec for " + repo + " " + str(version))
    return row


def install_commands(row: dict) -> list[str]:
    """Shell commands that install the official spec. requirements.txt is a separate file."""
    commands = ["python -m pip install --no-cache-dir pytest"]
    packages = row.get("packages")
    if isinstance(packages, str) and packages not in ("", "requirements.txt", "environment.yml"):
        commands.append("python -m pip install --no-cache-dir " + packages)
    elif packages == "requirements.txt":
        commands.append("python -m pip install --no-cache-dir -r /tmp/swebench-requirements.txt")
    elif packages == "environment.yml":
        raise ValueError("SWE-bench spec uses environment.yml; this builder only installs with pip")
    pip_packages = row.get("pip_packages") or []
    if pip_packages:
        commands.append("python -m pip install --no-cache-dir " + " ".join(pip_packages))
    for command in row.get("pre_install") or []:
        commands.append(command)
    if row.get("install"):
        commands.append(str(row["install"]))
    if not commands:
        raise ValueError("SWE-bench spec has no install commands")
    return commands


def fetch_requirements(repo: str, commit: str, version: str) -> str:
    _specs, paths = load_maps()
    relatives = paths.get(repo) or ["requirements.txt"]
    chunks = []
    for relative in relatives:
        url = "https://raw.githubusercontent.com/" + repo + "/" + commit + "/" + relative
        with urllib.request.urlopen(url, timeout=60) as response:
            chunks.append(response.read().decode("utf-8"))
    if not chunks:
        raise ValueError("no requirements for " + repo + " " + version)
    return "\n".join(chunks) + "\n"
