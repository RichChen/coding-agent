#!/usr/bin/env python3
"""Build a validated SWE-bench Lite local subset with fixture + oracle."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import posixpath
import re
import shutil
import subprocess
import sysconfig
import tarfile
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import patch_ng as patch
import requests
from datasets import load_dataset

RAW_GITHUB_BASE = "https://raw.githubusercontent.com"

PATCH_HINT_MARKERS = [
    "the following code fix",
    "i propose",
    "i thus propose",
    "proposed fix",
    "here is the fix",
    "the fix is",
    "### code fix",
    "# fix",
    "i have marked the",
]

REQUESTS_PYTHON_CMD = "%SWEBENCH_REQUESTS_PY%"


@dataclass
class SwebenchPyConstants:
    map_repo_version_to_specs: dict[str, dict[str, dict[str, Any]]]
    map_repo_to_reqs_paths: dict[str, list[str]]
    map_repo_to_install_py: dict[str, str]


@dataclass
class ValidationResult:
    instance_id: str
    repo: str
    accepted: bool
    reason: str
    fail_to_pass: list[str]
    pass_subset: list[str]
    fixture_dir: str | None = None
    fixture_size_bytes: int = 0


def _run(
    cmd: list[str],
    cwd: Path,
    timeout: int = 600,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        env=env,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def _run_shell(
    cmd: str,
    cwd: Path,
    timeout: int = 600,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        env=env,
        text=True,
        capture_output=True,
        timeout=timeout,
        shell=True,
        check=False,
    )


def _tail(proc: subprocess.CompletedProcess[str], n: int = 5) -> str:
    lines = (proc.stderr or proc.stdout or "").strip().splitlines()
    if not lines:
        return "no output"
    return " | ".join(lines[-n:])


def _load_swebench_py_constants() -> SwebenchPyConstants:
    constants_file = (
        Path(sysconfig.get_paths()["purelib"])
        / "swebench"
        / "harness"
        / "constants"
        / "python.py"
    )
    if not constants_file.exists():
        raise FileNotFoundError(f"SWE-bench constants not found: {constants_file}")
    spec = importlib.util.spec_from_file_location("swebench_constants_py", constants_file)
    if not spec or not spec.loader:
        raise RuntimeError("Failed to load SWE-bench constants module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return SwebenchPyConstants(
        map_repo_version_to_specs=module.MAP_REPO_VERSION_TO_SPECS_PY,
        map_repo_to_reqs_paths=module.MAP_REPO_TO_REQS_PATHS,
        map_repo_to_install_py=module.MAP_REPO_TO_INSTALL_PY,
    )


def _download_and_extract(repo: str, commit: str, out_dir: Path) -> Path:
    url = f"https://github.com/{repo}/archive/{commit}.tar.gz"
    archive_path = out_dir / "repo.tar.gz"
    last_error = ""
    for attempt in range(1, 4):
        try:
            with requests.get(url, stream=True, timeout=90) as resp:
                resp.raise_for_status()
                with archive_path.open("wb") as f:
                    for chunk in resp.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            f.write(chunk)
            break
        except Exception as e:  # noqa: BLE001
            last_error = str(e)
            if attempt == 3:
                raise RuntimeError(last_error) from e
            time.sleep(attempt * 2)
    with tarfile.open(archive_path, "r:gz") as tar:
        tar.extractall(out_dir)
    dirs = [p for p in out_dir.iterdir() if p.is_dir()]
    if not dirs:
        raise RuntimeError(f"No extracted directory for {repo}@{commit}")
    return sorted(dirs)[0]


def _apply_patch(repo_root: Path, patch_text: str) -> bool:
    patch_set = patch.fromstring(patch_text.encode("utf-8"))
    return patch_set.apply(root=str(repo_root))


def _changed_files_from_patch(patch_text: str) -> list[Path]:
    changed: list[Path] = []
    for line in patch_text.splitlines():
        if line.startswith("+++ b/"):
            rel = line[len("+++ b/") :].strip()
            if rel and rel != "/dev/null":
                changed.append(Path(rel))
    uniq: list[Path] = []
    seen: set[str] = set()
    for p in changed:
        key = str(p)
        if key not in seen:
            uniq.append(p)
            seen.add(key)
    return uniq


def _safe_name(instance_id: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", instance_id)


def _subset_tests(tests: list[str], limit: int) -> list[str]:
    return tests[: max(0, limit)]


def _test_files_from_patch(test_patch_text: str) -> list[str]:
    files: list[str] = []
    for rel in _changed_files_from_patch(test_patch_text):
        rel_s = str(rel).replace("\\", "/")
        if rel_s.endswith(".py") and ("test" in rel_s or "/tests/" in rel_s):
            files.append(rel_s)
    seen: set[str] = set()
    uniq: list[str] = []
    for f in files:
        if f not in seen:
            seen.add(f)
            uniq.append(f)
    return uniq


def _protected_from_assertions(task: dict) -> list[str]:
    """Extract .py paths from assertion pytest commands (offline backfill)."""
    py_token = re.compile(r"[\w./-]+\.py")
    found: list[str] = []
    seen: set[str] = set()
    expected = task.get("expected", {})
    assertions = expected.get("assertions", [])
    if expected.get("type") != "multi_assert":
        assertions = [expected] if expected.get("command") else []
    for assertion in assertions:
        cmd = assertion.get("command", "")
        for match in py_token.findall(cmd):
            normalized = match.replace("\\", "/")
            if normalized not in seen:
                seen.add(normalized)
                found.append(normalized)
    return found


def _parse_test_names(tests: list[str]) -> list[str]:
    names: list[str] = []
    for test in tests:
        if "::" in test:
            tail = test.split("::")[-1]
            names.append(tail.split("[")[0])
        elif test.endswith(".py"):
            continue
        else:
            names.append(test.split("[")[0])
    return [n for n in names if n]


def _build_pytest_cmd(py: str, tests: list[str], test_patch_text: str) -> list[str]:
    named = [t for t in tests if "::" in t or t.endswith(".py")]
    bare = [t for t in tests if t not in named]
    cmd = [py, "-m", "pytest", "-q"]
    if named:
        cmd.extend(named)
    elif bare:
        files = _test_files_from_patch(test_patch_text)
        if files:
            cmd.extend(files)
            cmd.extend(["-k", " or ".join(_parse_test_names(bare))])
        else:
            cmd.extend(bare)
    return cmd


def _pytest_command_str(tests: list[str], test_patch_text: str, python_cmd: str = "python") -> str:
    cmd = _build_pytest_cmd(python_cmd, tests, test_patch_text)
    parts: list[str] = []
    for token in cmd:
        if token.startswith("%") and token.endswith("%"):
            parts.append(token)
            continue
        if re.fullmatch(r"[A-Za-z0-9_./:=+-]+", token):
            parts.append(token)
            continue
        escaped = token.replace("\"", "\\\"")
        parts.append(f"\"{escaped}\"")
    return "set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 && " + " ".join(parts)


def _sanitize_problem(text: str, instance_id: str = "") -> str:
    lower = text.lower()
    cut_pos = len(text)
    for marker in PATCH_HINT_MARKERS:
        idx = lower.find(marker)
        if idx != -1 and idx < cut_pos:
            cut_pos = idx
    if cut_pos < len(text):
        sanitized = " ".join(text[:cut_pos].split())
        if len(sanitized) < 80:
            print(
                json.dumps(
                    {
                        "warn": "sanitize too aggressive",
                        "instance_id": instance_id,
                        "sanitized_len": len(sanitized),
                    },
                    ensure_ascii=False,
                )
            )
            return " ".join(text.split())
        return sanitized
    return " ".join(text.split())


def _repo_tag(repo: str) -> str:
    return repo.split("/")[-1]


def _detect_python_version(py: Path) -> str:
    proc = _run([str(py), "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"], cwd=Path.cwd())
    if proc.returncode != 0:
        return ""
    return (proc.stdout or "").strip()


def _find_env_python(env_dir: Path) -> Path | None:
    candidates = [
        env_dir / "python.exe",
        env_dir / "Scripts" / "python.exe",
        env_dir / "bin" / "python",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def _create_python_env(base_python: str, required_python: str, env_dir: Path) -> Path:
    env_dir = env_dir.resolve()
    env_dir.parent.mkdir(parents=True, exist_ok=True)
    base_py = Path(base_python)
    if not base_py.exists():
        raise RuntimeError(f"base python missing: {base_python}")
    base_version = _detect_python_version(base_py)

    if base_version == required_python:
        _run([str(base_py), "-m", "pip", "install", "-q", "virtualenv"], cwd=env_dir.parent, timeout=300)
        create = _run([str(base_py), "-m", "virtualenv", str(env_dir)], cwd=env_dir.parent, timeout=600)
        py = _find_env_python(env_dir)
        if create.returncode == 0 and py:
            return py
        return base_py

    py_launcher = _run(["py", f"-{required_python}", "-V"], cwd=env_dir.parent, timeout=60)
    if py_launcher.returncode == 0:
        create = _run(["py", f"-{required_python}", "-m", "virtualenv", str(env_dir)], cwd=env_dir.parent, timeout=600)
        py = _find_env_python(env_dir)
        if create.returncode == 0 and py:
            return py

    if env_dir.exists():
        shutil.rmtree(env_dir, ignore_errors=True)
    conda_create = _run(
        ["conda", "create", "-p", str(env_dir), f"python={required_python}", "-y", "--solver=classic"],
        cwd=env_dir.parent,
        timeout=1800,
    )
    py = _find_env_python(env_dir)
    if conda_create.returncode == 0 and py:
        return py
    raise RuntimeError(f"cannot provision python {required_python}: {_tail(conda_create)}")


def _replace_python_cmd(cmd: str, py: Path) -> str:
    text = cmd.strip()
    if text.startswith("python "):
        return f"\"{py}\" {text[len('python '):]}"
    if text == "python":
        return f"\"{py}\""
    return text


def _fetch_requirements_text(
    repo: str,
    commit: str,
    req_paths: list[str],
) -> str | None:
    for req_path in req_paths:
        url = f"{RAW_GITHUB_BASE}/{repo}/{commit}/{req_path}"
        try:
            resp = requests.get(url, timeout=40)
            if resp.status_code == 200:
                return resp.text
        except Exception:  # noqa: BLE001
            continue
    return None


def _flatten_requirements(
    repo: str,
    commit: str,
    req_path: str,
    body: str,
    visited: set[str],
) -> list[str]:
    if req_path in visited:
        return []
    visited.add(req_path)
    req_dir = posixpath.dirname(req_path)
    rows: list[str] = []
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("-e .") or line.startswith(".[test"):
            continue
        if line.startswith("-r"):
            include_name = line[2:].strip()
            include_path = posixpath.normpath(posixpath.join(req_dir, include_name))
            include_text = _fetch_requirements_text(repo, commit, [include_path])
            if include_text:
                rows.extend(_flatten_requirements(repo, commit, include_path, include_text, visited))
            continue
        rows.append(line)
    return rows


def _fetch_flattened_requirements(
    repo: str,
    commit: str,
    req_paths: list[str],
) -> str | None:
    for req_path in req_paths:
        body = _fetch_requirements_text(repo, commit, [req_path])
        if not body:
            continue
        lines = _flatten_requirements(repo, commit, req_path, body, visited=set())
        cleaned = [("types-setuptools" if x.startswith("types-pkg_resources") else x) for x in lines]
        return "\n".join(cleaned) + "\n"
    return None


def _install_from_specs(
    py: Path,
    repo_root: Path,
    row: dict[str, Any],
    specs: dict[str, Any],
    constants: SwebenchPyConstants,
) -> tuple[bool, str]:
    _run([str(py), "-m", "pip", "install", "-q", "--upgrade", "pip"], cwd=repo_root, timeout=300)
    _run([str(py), "-m", "pip", "install", "-q", "pytest"], cwd=repo_root, timeout=300)

    packages = specs.get("packages", "")
    if packages == "requirements.txt":
        commit = row.get("environment_setup_commit") or row["base_commit"]
        req_paths = constants.map_repo_to_reqs_paths.get(row["repo"], ["requirements.txt"])
        req_text = _fetch_flattened_requirements(row["repo"], commit, req_paths)
        if req_text:
            req_file = repo_root / "_swebench_requirements.txt"
            req_file.write_text(req_text, encoding="utf-8")
            install = _run([str(py), "-m", "pip", "install", "-q", "-r", str(req_file.resolve())], cwd=repo_root, timeout=900)
            if req_file.exists():
                req_file.unlink()
            if install.returncode != 0:
                return False, f"requirements install failed: {_tail(install)}"
    elif packages and packages != "environment.yml":
        pkg_tokens = [x for x in str(packages).split() if x]
        if pkg_tokens:
            install = _run([str(py), "-m", "pip", "install", "-q", *pkg_tokens], cwd=repo_root, timeout=900)
            if install.returncode != 0:
                return False, f"packages install failed: {_tail(install)}"

    pip_packages = specs.get("pip_packages", [])
    if pip_packages:
        install = _run([str(py), "-m", "pip", "install", "-q", *pip_packages], cwd=repo_root, timeout=1200)
        if install.returncode != 0:
            return False, f"pip_packages install failed: {_tail(install)}"

    if row["repo"] in constants.map_repo_to_install_py:
        cmd = _replace_python_cmd(constants.map_repo_to_install_py[row["repo"]], py)
        install = _run_shell(cmd, cwd=repo_root, timeout=900)
        if install.returncode != 0:
            return False, f"repo install hook failed: {_tail(install)}"

    pre_install = specs.get("pre_install", [])
    for cmd in pre_install:
        run = _run_shell(_replace_python_cmd(cmd, py), cwd=repo_root, timeout=1200)
        if run.returncode != 0:
            return False, f"pre_install failed: {_tail(run)}"

    if "install" in specs:
        cmd = _replace_python_cmd(str(specs["install"]), py)
        run = _run_shell(cmd, cwd=repo_root, timeout=1200)
        if run.returncode != 0:
            return False, f"install failed: {_tail(run)}"

    return True, "ok"


def _dir_size_bytes(path: Path) -> int:
    total = 0
    for p in path.rglob("*"):
        if p.is_file():
            total += p.stat().st_size
    return total


def _run_pytest(cmd: list[str], cwd: Path, timeout: int) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    return _run(cmd, cwd=cwd, timeout=timeout, env=env)


def validate_and_materialize(
    row: dict[str, Any],
    *,
    base_python: str,
    fixture_root: Path,
    pass_subset_limit: int,
    work_root: Path,
    constants: SwebenchPyConstants,
) -> ValidationResult:
    instance_id = row["instance_id"]
    repo = row["repo"]
    fail_to_pass = json.loads(row["FAIL_TO_PASS"])
    pass_to_pass = json.loads(row["PASS_TO_PASS"])
    pass_subset = _subset_tests(pass_to_pass, pass_subset_limit)

    if not fail_to_pass:
        return ValidationResult(instance_id, repo, False, "FAIL_TO_PASS empty", fail_to_pass, pass_subset)

    repo_specs = constants.map_repo_version_to_specs.get(repo, {})
    specs = repo_specs.get(row["version"])
    if not specs:
        return ValidationResult(instance_id, repo, False, f"missing specs for {repo}@{row['version']}", fail_to_pass, pass_subset)

    required_python = str(specs.get("python", "3.11"))

    with tempfile.TemporaryDirectory(prefix="swebench_", dir=work_root.resolve()) as tmp:
        tmp_dir = Path(tmp).resolve()
        try:
            repo_root = _download_and_extract(repo, row["base_commit"], tmp_dir)
        except Exception as e:  # noqa: BLE001
            return ValidationResult(instance_id, repo, False, f"download/extract failed: {e}", fail_to_pass, pass_subset)

        try:
            py = _create_python_env(base_python, required_python, tmp_dir / "env")
        except Exception as e:  # noqa: BLE001
            return ValidationResult(instance_id, repo, False, f"python {required_python} env failed: {e}", fail_to_pass, pass_subset)

        ok, reason = _install_from_specs(py, repo_root, row, specs, constants)
        if not ok:
            return ValidationResult(instance_id, repo, False, reason, fail_to_pass, pass_subset)

        if not _apply_patch(repo_root, row["test_patch"]):
            return ValidationResult(instance_id, repo, False, "apply test_patch failed", fail_to_pass, pass_subset)

        fixture_snapshot = tmp_dir / "fixture_snapshot"
        shutil.copytree(repo_root, fixture_snapshot, dirs_exist_ok=True)

        fail_cmd = _build_pytest_cmd(py, fail_to_pass, row["test_patch"])
        fail_before = _run_pytest(fail_cmd, cwd=repo_root, timeout=1200)
        if fail_before.returncode == 0:
            return ValidationResult(instance_id, repo, False, "FAIL_TO_PASS unexpectedly passes before gold patch", fail_to_pass, pass_subset)

        if not _apply_patch(repo_root, row["patch"]):
            return ValidationResult(instance_id, repo, False, "apply gold patch failed", fail_to_pass, pass_subset)

        fail_after = _run_pytest(fail_cmd, cwd=repo_root, timeout=1200)
        if fail_after.returncode != 0:
            return ValidationResult(instance_id, repo, False, f"FAIL_TO_PASS still fails after gold patch: {_tail(fail_after)}", fail_to_pass, pass_subset)

        if pass_subset:
            pass_cmd = _build_pytest_cmd(py, pass_subset, row["test_patch"])
            pass_res = _run_pytest(pass_cmd, cwd=repo_root, timeout=1200)
            if pass_res.returncode != 0:
                return ValidationResult(instance_id, repo, False, f"PASS_TO_PASS subset fails after gold patch: {_tail(pass_res)}", fail_to_pass, pass_subset)

        fixture_name = f"swebench_{_safe_name(instance_id)}"
        fixture_dir = fixture_root / fixture_name
        if fixture_dir.exists():
            shutil.rmtree(fixture_dir)
        shutil.copytree(fixture_snapshot, fixture_dir)

        for remove_name in [".git", ".github", "docs", "examples", "benchmarks"]:
            target = fixture_dir / remove_name
            if target.exists() and target.is_dir():
                shutil.rmtree(target, ignore_errors=True)

        oracle_dir = fixture_dir / ".oracle"
        oracle_dir.mkdir(parents=True, exist_ok=True)
        for rel in _changed_files_from_patch(row["patch"]):
            src = repo_root / rel
            if src.exists() and src.is_file():
                dst = oracle_dir / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)

        setup_md = fixture_dir / "SETUP.md"
        setup_md.write_text(
            "\n".join(
                [
                    f"# SWE-bench fixture: {instance_id}",
                    "",
                    f"- repo: `{repo}`",
                    f"- base_commit: `{row['base_commit']}`",
                    f"- environment_setup_commit: `{row.get('environment_setup_commit', row['base_commit'])}`",
                    f"- version: `{row.get('version', 'unknown')}`",
                    f"- swebench_python: `{required_python}`",
                    f"- swebench_packages: `{specs.get('packages', '')}`",
                    f"- swebench_pip_packages: `{specs.get('pip_packages', [])}`",
                    f"- swebench_install: `{specs.get('install', '')}`",
                ]
            ),
            encoding="utf-8",
        )

        size_bytes = _dir_size_bytes(fixture_dir)
        return ValidationResult(
            instance_id=instance_id,
            repo=repo,
            accepted=True,
            reason="validated and materialized",
            fail_to_pass=fail_to_pass,
            pass_subset=pass_subset,
            fixture_dir=str(fixture_dir).replace("\\", "/"),
            fixture_size_bytes=size_bytes,
        )


def make_task_entry(row: dict[str, Any], result: ValidationResult, *, python_cmd: str = "python") -> dict[str, Any]:
    assert result.fixture_dir is not None
    repo_tag = _repo_tag(row["repo"])
    problem = _sanitize_problem(row["problem_statement"], row["instance_id"])
    assertions = [
        {
            "type": "command_success",
            "command": _pytest_command_str(result.fail_to_pass, row["test_patch"], python_cmd=python_cmd),
            "timeout": 300,
        }
    ]
    if result.pass_subset:
        assertions.append(
            {
                "type": "command_success",
                "command": _pytest_command_str(result.pass_subset, row["test_patch"], python_cmd=python_cmd),
                "timeout": 300,
            }
        )
    return {
        "id": f"swebench_{_safe_name(row['instance_id'])}",
        "description": (
            f"[SWE-bench Lite {row['instance_id']}] {problem} "
            "Do not use .oracle files and do not modify tests."
        ),
        "fixture_dir": result.fixture_dir,
        "expected": {"type": "multi_assert", "assertions": assertions},
        "protected_paths": _test_files_from_patch(row["test_patch"]),
        "difficulty": "hard",
        "tags": ["swebench", repo_tag, "external-benchmark", "hard"],
    }


def _read_jsonl_candidates(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    raw = path.read_bytes()
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        text = raw.decode("utf-16")
    else:
        text = raw.decode("utf-8")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    meta = json.loads(lines[0])
    return meta, [json.loads(line) for line in lines[1:]]


def refresh_task_descriptions(dataset_path: Path) -> int:
    with dataset_path.open(encoding="utf-8") as f:
        dataset = json.load(f)
    ds = load_dataset("princeton-nlp/SWE-bench_Lite", split="test")
    by_id = {row["instance_id"]: row for row in ds}
    updated = 0
    for task in dataset["tasks"]:
        task_key = task["id"]
        if not task_key.startswith("swebench_"):
            continue
        instance_id = task_key[len("swebench_") :]
        row = by_id.get(instance_id)
        if not row:
            continue
        problem = _sanitize_problem(row["problem_statement"], instance_id)
        task["description"] = (
            f"[SWE-bench Lite {instance_id}] {problem} "
            "Do not use .oracle files and do not modify tests."
        )
        updated += 1
    dataset_path.write_text(json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"refreshed_descriptions": updated, "dataset": str(dataset_path)}, ensure_ascii=False))
    return 0


def refresh_requests_commands(dataset_path: Path) -> int:
    with dataset_path.open(encoding="utf-8") as f:
        dataset = json.load(f)
    updated = 0
    legacy = '"D:\\crq\\src\\coding-harness\\.tmp\\swebench_oracle_py39\\python.exe"'
    for task in dataset["tasks"]:
        if "requests" not in task.get("tags", []):
            continue
        expected = task.get("expected", {})
        if expected.get("type") != "multi_assert":
            continue
        for assertion in expected.get("assertions", []):
            cmd = assertion.get("command", "")
            if legacy in cmd or ".tmp" in cmd or "swebench_oracle_py39" in cmd:
                assertion["command"] = cmd.replace(legacy, REQUESTS_PYTHON_CMD)
                updated += 1
    dataset_path.write_text(json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"refreshed_request_commands": updated, "dataset": str(dataset_path)}, ensure_ascii=False))
    return 0


def refresh_protected_paths(dataset_path: Path) -> int:
    with dataset_path.open(encoding="utf-8") as f:
        dataset = json.load(f)
    counts: dict[str, int] = {}
    for task in dataset["tasks"]:
        if not task["id"].startswith("swebench_"):
            continue
        protected = _protected_from_assertions(task)
        task["protected_paths"] = protected
        counts[task["id"]] = len(protected)
        print(f"{task['id']}: {len(protected)} protected path(s)")
    dataset_path.write_text(json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"refreshed_protected_paths": counts, "dataset": str(dataset_path)}, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Build SWE-bench Lite subset fixtures")
    parser.add_argument("--candidate-file", default="swebench_candidates.jsonl")
    parser.add_argument("--target-count", type=int, default=8)
    parser.add_argument("--min-repos", type=int, default=3)
    parser.add_argument("--pass-subset-limit", type=int, default=10)
    parser.add_argument(
        "--python",
        default=r"C:\Users\Administrator\.conda\envs\coding-harness\python.exe",
    )
    parser.add_argument("--fixture-root", default="tests/fixtures/repos")
    parser.add_argument("--dataset-out", default="datasets/swebench_lite_tasks.json")
    parser.add_argument("--log-out", default="reports/examples/swebench_lite_validation_log.json")
    parser.add_argument("--work-root", default=".tmp/swebench_build")
    parser.add_argument(
        "--refresh-descriptions",
        action="store_true",
        help="Only refresh task descriptions in an existing dataset JSON",
    )
    parser.add_argument(
        "--refresh-requests-commands",
        action="store_true",
        help="Replace requests task absolute python paths with %SWEBENCH_REQUESTS_PY%",
    )
    parser.add_argument(
        "--refresh-protected",
        action="store_true",
        help="Backfill protected_paths from assertion pytest commands (offline)",
    )
    parser.add_argument(
        "--oracle-python-3-9",
        default=".tmp/swebench_oracle_py39/python.exe",
        help="Python 3.9 executable used during validation/build (not written to dataset)",
    )
    args = parser.parse_args()

    dataset_out = Path(args.dataset_out)
    if args.refresh_descriptions:
        return refresh_task_descriptions(dataset_out)
    if args.refresh_requests_commands:
        return refresh_requests_commands(dataset_out)
    if args.refresh_protected:
        return refresh_protected_paths(dataset_out)

    constants = _load_swebench_py_constants()
    meta, candidates = _read_jsonl_candidates(Path(args.candidate_file))
    ds = load_dataset("princeton-nlp/SWE-bench_Lite", split=meta.get("split", "test"))
    by_id = {row["instance_id"]: row for row in ds}

    fixture_root = Path(args.fixture_root)
    fixture_root.mkdir(parents=True, exist_ok=True)
    work_root = Path(args.work_root)
    work_root.mkdir(parents=True, exist_ok=True)

    accepted: list[ValidationResult] = []
    logs: list[dict[str, Any]] = []

    for candidate in candidates:
        instance_id = candidate["instance_id"]
        row = by_id.get(instance_id)
        if not row:
            log = {"instance_id": instance_id, "accepted": False, "reason": "not found in split"}
            logs.append(log)
            print(json.dumps(log, ensure_ascii=False))
            continue

        result = validate_and_materialize(
            row,
            base_python=args.python,
            fixture_root=fixture_root,
            pass_subset_limit=args.pass_subset_limit,
            work_root=work_root,
            constants=constants,
        )
        log = {
            "instance_id": result.instance_id,
            "repo": result.repo,
            "accepted": result.accepted,
            "reason": result.reason,
            "fail_to_pass": result.fail_to_pass,
            "pass_subset": result.pass_subset,
            "fixture_dir": result.fixture_dir,
            "fixture_size_bytes": result.fixture_size_bytes,
        }
        logs.append(log)
        print(json.dumps(log, ensure_ascii=False))
        if result.accepted:
            accepted.append(result)
        accepted_repo_count = len({x.repo for x in accepted})
        if len(accepted) >= args.target_count and accepted_repo_count >= args.min_repos:
            break

    oracle_py39 = Path(args.oracle_python_3_9)
    if not oracle_py39.exists():
        provisioned = _create_python_env(args.python, "3.9", oracle_py39.parent)
        _run([str(provisioned), "-m", "pip", "install", "-q", "pytest"], cwd=Path.cwd(), timeout=600)
        oracle_py39 = provisioned
    else:
        oracle_py39 = oracle_py39.resolve()

    tasks: list[dict[str, Any]] = []
    for result in accepted:
        row = by_id[result.instance_id]
        specs = constants.map_repo_version_to_specs.get(row["repo"], {}).get(row["version"], {})
        python_cmd = "python"
        spec_python = str(specs.get("python", ""))
        if spec_python == "3.9" and row["repo"] == "psf/requests":
            python_cmd = REQUESTS_PYTHON_CMD
        tasks.append(make_task_entry(row, result, python_cmd=python_cmd))
    dataset = {
        "name": "swebench_lite_tasks",
        "description": "Validated SWE-bench Lite subset for local harness eval",
        "version": "0.2.0",
        "source_dataset": "princeton-nlp/SWE-bench_Lite",
        "tasks": tasks,
    }

    dataset_out = Path(args.dataset_out)
    dataset_out.parent.mkdir(parents=True, exist_ok=True)
    dataset_out.write_text(json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8")

    total_fixture_bytes = sum(x.fixture_size_bytes for x in accepted)
    repo_count = len({x.repo for x in accepted})
    summary = {
        "target_count": args.target_count,
        "accepted_count": len(tasks),
        "accepted_repo_count": repo_count,
        "total_fixture_size_bytes": total_fixture_bytes,
        "dataset_out": str(dataset_out).replace("\\", "/"),
        "log_out": str(Path(args.log_out)).replace("\\", "/"),
    }

    log_out = Path(args.log_out)
    log_out.parent.mkdir(parents=True, exist_ok=True)
    log_out.write_text(json.dumps({"runs": logs, "summary": summary}, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
