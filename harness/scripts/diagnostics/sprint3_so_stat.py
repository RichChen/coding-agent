"""After applying a saved delta, print the check_build directory. No model calls."""
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.preflight_a5_repo_baseline import prepare_repo_runtime, upload_runner
from scripts.regrade_saved_delta import normalize_delta
from scripts.run_swe_task import grader_spec, load_yaml
from src.eval.image_grader import APPLY
from src.execution.base import ExecutionRequest, OutputQuotas
from src.execution.docker import DockerExecutionBackend


async def main():
    run_dir = Path(sys.argv[1])
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    task = next(item for item in load_yaml(ROOT / "configs/sprint/dev-tasks.yaml")["tasks"] if item["id"] == summary["task_id"])
    spec = grader_spec(task)
    delta = normalize_delta(json.loads((run_dir / "candidate-delta.json").read_text(encoding="utf-8"))) if len(sys.argv) > 2 else {"changed": {}, "deleted": []}
    backend = DockerExecutionBackend(image=spec.image, context="desktop-linux", memory_bytes=2 * 1024**3, workspace_bytes=512 * 1024**2, tmpfs_bytes=256 * 1024**2, network="none")
    await backend.start({})
    try:
        await prepare_repo_runtime(backend)
        payload = {"deleted": [], "changed": delta.get("changed") or {}, "overlay": spec.test_overlay}
        await backend._ok("exec", "-i", backend.name, "/usr/local/bin/python", "-I", "-S", "-c", APPLY, data=json.dumps(payload).encode(), limit=64 * 1024, timeout=120)
        await upload_runner(backend, django=False)
        nodes = [
            "sklearn/linear_model/tests/test_ridge.py::test_ridge_classifier_cv_store_cv_values",
            "sklearn/linear_model/tests/test_ridge.py::test_ridge",
        ]
        request = ExecutionRequest(
            argv=["/usr/local/bin/python", "-I", "-B", "/tmp/a5-runner.py"],
            stdin_bytes=json.dumps({"args": nodes, "labels": nodes, "collect_only": False, "sympy_native_helpers": False}).encode(),
            env={"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTHONPATH": "/workspace:/workspace/src", "A5_REPO_ROOT": "/workspace", "PYTHONDONTWRITEBYTECODE": "1"},
            deadline_mono=__import__("time").monotonic() + 180,
            quotas=OutputQuotas(memory_per_stream_bytes=4 * 1024**2, artifact_per_tool_bytes=16 * 1024**2),
        )
        execution = await backend.execute(request)
        raw = await backend._ok("exec", backend.name, "/usr/local/bin/python", "-I", "-S", "-c",
            "print(open('/tmp/a5-pytest-receipt.json').read())", limit=64 * 1024, timeout=30)
        receipt = json.loads(raw)
        err = (receipt.get("collection_errors") or [""])[0]
        print(json.dumps({"status": execution.status.value, "collected": len(receipt.get("collected") or []), "exit": receipt.get("exit_code"), "error": str(err)[:400], "stderr": (execution.stderr.text_preview or "")[-500:]}, ensure_ascii=False))
    finally:
        await backend.close()


if __name__ == "__main__":
    asyncio.run(main())
