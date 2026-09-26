"""Grade a candidate delta inside the baseline image. The source tree is not uploaded."""
from __future__ import annotations

import base64
import json
import time
from pathlib import Path

from src.execution.base import ExecutionRequest, OutputQuotas
from src.execution.baseline_image_backend import is_export_skipped
from src.execution.docker import DockerExecutionBackend

APPLY = r'''
import base64, json, pathlib, sys
req = json.load(sys.stdin)
root = pathlib.Path("/workspace")
for name in req.get("deleted") or []:
    path = root / name
    if path.is_file() or path.is_symlink():
        path.unlink()
for name, encoded in (req.get("changed") or {}).items():
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(base64.b64decode(encoded))
for name, encoded in (req.get("overlay") or {}).items():
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(base64.b64decode(encoded))
'''

CONFIG_NAMES = {"conftest.py", "setup.cfg", "setup.py", "pyproject.toml", "pytest.ini", "tox.ini", "setup.cfg"}


def touched_kinds(paths: list[str]) -> dict:
    tests, configs = [], []
    for name in paths:
        base = Path(name).name
        if base in CONFIG_NAMES or base == "conftest.py":
            configs.append(name)
        if "/tests/" in name or "/test/" in name or base.startswith("test_") or base == "conftest.py":
            tests.append(name)
    return {"test_files_touched": tests, "config_files_touched": configs}


def score_receipt(receipt: dict | None, f2p: list[str], p2p: list[str]) -> dict:
    """Judge each node id from the receipt. Exit codes and printed counts are not used."""
    from scripts.preflight_a5_repo_baseline import outcomes

    by_id = outcomes(receipt or {})
    def count(nodes):
        passed = sum(1 for node in nodes if by_id.get(node) == "passed")
        return passed, len(nodes)
    f2p_passed, f2p_total = count(f2p)
    p2p_passed, p2p_total = count(p2p)
    missing = [node for node in f2p + p2p if node not in by_id]
    solved = f2p_total > 0 and f2p_passed == f2p_total and p2p_passed == p2p_total and not missing
    status = "pass" if solved else "partial" if receipt else "invalid_env"
    if receipt and not solved:
        status = "fail" if f2p_passed == 0 else "partial"
    return {
        "status": status,
        "solved": solved,
        "f2p_passed": f2p_passed,
        "f2p_total": f2p_total,
        "p2p_passed": p2p_passed,
        "p2p_total": p2p_total,
        "cases": [{"nodeid": node, "outcome": by_id.get(node, "missing")} for node in f2p + p2p],
        "reason": None if receipt else "missing_receipt",
    }


def receipt_diagnostics(receipt: dict | None) -> dict:
    """Host-only grader notes. These must not be copied into the agent prompt."""
    errors = []
    for item in (receipt or {}).get("collection_errors") or []:
        text = item if isinstance(item, str) else json.dumps(item, default=str)
        errors.append(text[:2048])
        if len(errors) >= 20:
            break
    collected = (receipt or {}).get("collected") or []
    return {
        "collected_count": len(collected) if isinstance(collected, list) else 0,
        "collection_errors": errors,
        "runner_error": (receipt or {}).get("runner_error"),
        "exit_code": (receipt or {}).get("exit_code"),
    }


class ImageGrader:
    def __init__(self, *, context: str = "desktop-linux"):
        self.context = context

    async def evaluate(self, *, image: str, delta: dict | None, test_overlay: dict, f2p: list[str], p2p: list[str], django: bool = False, sympy: bool = False, timeout: float = 300, repo_root: str = "/opt/repo", python_bin: str = "/usr/local/bin/python") -> dict:
        from scripts.preflight_a5_repo_baseline import prepare_repo_runtime, upload_runner

        backend = DockerExecutionBackend(
            image=image, context=self.context, memory_bytes=2 * 1024**3,
            workspace_bytes=512 * 1024**2, tmpfs_bytes=256 * 1024**2, network="none",
            python_bin=python_bin,
        )
        result = {"status": "invalid_env", "solved": False, "reason": None}
        try:
            await backend.start({})
            await prepare_repo_runtime(backend, repo_root=repo_root, python_bin=python_bin)
            payload = {
                "deleted": [name for name in ((delta or {}).get("deleted") or []) if not is_export_skipped(name)],
                "changed": {
                    name: encoded
                    for name, encoded in ((delta or {}).get("changed") or {}).items()
                    if not is_export_skipped(name)
                },
                "overlay": test_overlay or {},
            }
            await backend._ok(
                "exec", "-i", backend.name, python_bin, "-I", "-S", "-c", APPLY,
                data=json.dumps(payload).encode(), limit=64 * 1024, timeout=120,
            )
            await upload_runner(backend, django=django, python_bin=python_bin)
            nodeids = list(f2p) + list(p2p)
            request = ExecutionRequest(
                argv=[python_bin, "-I", "-B", "/tmp/a5-runner.py"],
                stdin_bytes=json.dumps({
                    "args": nodeids, "labels": nodeids, "collect_only": False,
                    "sympy_native_helpers": sympy,
                }).encode(),
                env={
                    "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
                    "PYTHONPATH": "/workspace:/workspace/src",
                    "A5_REPO_ROOT": "/workspace",
                    "PYTHONDONTWRITEBYTECODE": "1",
                },
                deadline_mono=time.monotonic() + timeout,
                quotas=OutputQuotas(memory_per_stream_bytes=4 * 1024**2, artifact_per_tool_bytes=16 * 1024**2),
            )
            execution = await backend.execute(request)
            result["execution_status"] = execution.status.value
            result["execution_stderr_tail"] = (execution.stderr.text_preview or "")[-4096:]
            raw = await backend._ok(
                "exec", backend.name, python_bin, "-I", "-S", "-c",
                "from pathlib import Path; import sys; p=Path('/tmp/a5-pytest-receipt.json'); sys.stdout.buffer.write(p.read_bytes())",
                limit=16 * 1024**2,
            )
            receipt = json.loads(raw)
            result.update(score_receipt(receipt, f2p, p2p))
            result.update(receipt_diagnostics(receipt))
            result["receipt_complete"] = receipt.get("complete")
        except Exception as exc:
            result["reason"] = type(exc).__name__ + ": " + str(exc)[:500]
        finally:
            await backend.close()
        changed = list(((delta or {}).get("changed") or {}).keys()) + list((delta or {}).get("deleted") or [])
        result.update(touched_kinds(changed))
        return result
