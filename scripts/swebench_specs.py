"""Read SWE-bench's per-version install specs. Do not hand-write dependency pins."""
from __future__ import annotations

import importlib.util
import posixpath
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


def _cython_token(row: dict) -> str | None:
    """Bare 'cython' on today's PyPI is Cython 3, which cannot compile the 0.2x trees."""
    packages = row.get("packages") or ""
    if isinstance(packages, str):
        for part in packages.replace("'", " ").split():
            if part.startswith("cython=="):
                return part
    if str(row.get("python") or "") in {"3.5", "3.6"}:
        return "cython==0.29.37"
    return None


def _with_cython_pin(token: str, pin: str | None) -> str:
    return pin if token == "cython" and pin else token


def install_commands(row: dict) -> list[str]:
    """Shell commands that install the official spec. requirements.txt is a separate file."""
    pin = _cython_token(row)
    commands = ["python -m pip install --no-cache-dir pytest"]
    packages = row.get("packages")
    if isinstance(packages, str) and packages not in ("", "requirements.txt", "environment.yml"):
        pinned = " ".join(_with_cython_pin(part, pin) for part in packages.split())
        commands.append("python -m pip install --no-cache-dir " + pinned)
    elif packages == "requirements.txt":
        commands.append("python -m pip install --no-cache-dir -r /tmp/swebench-requirements.txt")
    elif packages == "environment.yml":
        raise ValueError("SWE-bench spec uses environment.yml; this builder only installs with pip")
    pip_packages = [_with_cython_pin(part, pin) for part in (row.get("pip_packages") or [])]
    if pip_packages:
        commands.append("python -m pip install --no-cache-dir " + " ".join(pip_packages))
    for command in row.get("pre_install") or []:
        commands.append(command)
    if row.get("install"):
        commands.append(str(row["install"]))
    if not commands:
        raise ValueError("SWE-bench spec has no install commands")
    return commands


def _fetch_text(repo: str, commit: str, relative: str) -> str:
    url = "https://raw.githubusercontent.com/" + repo + "/" + commit + "/" + relative
    with urllib.request.urlopen(url, timeout=60) as response:
        return response.read().decode("utf-8")


def _flatten_requirements(repo: str, commit: str, relative: str, text: str, seen: set[str]) -> str:
    base = posixpath.dirname(relative)
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("-r ") or stripped.startswith("--requirement "):
            child = posixpath.normpath(posixpath.join(base, stripped.split(None, 1)[1]))
            if child in seen:
                continue
            seen.add(child)
            lines.append(_flatten_requirements(repo, commit, child, _fetch_text(repo, commit, child), seen))
        else:
            lines.append(line)
    return "\n".join(lines)


def fetch_requirements(repo: str, commit: str, version: str) -> str:
    _specs, paths = load_maps()
    relatives = paths.get(repo) or ["requirements.txt"]
    chunks = []
    seen = set(relatives)
    for relative in relatives:
        chunks.append(_flatten_requirements(repo, commit, relative, _fetch_text(repo, commit, relative), seen))
    if not any(chunk.strip() for chunk in chunks):
        raise ValueError("no requirements for " + repo + " " + version)
    return "\n".join(chunks) + "\n"
