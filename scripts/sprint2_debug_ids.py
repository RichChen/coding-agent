import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.preflight_a5_repo_baseline import prepare_repo_runtime, upload_runner
from scripts.sprint2_calibrate import spec_ids
from src.execution.base import ExecutionRequest, OutputQuotas
from src.execution.docker import DockerExecutionBackend


async def main():
    task = Path(sys.argv[1])
    receipt, family, f2p, p2p, overlay = spec_ids(task)
    backend = DockerExecutionBackend(
        image=receipt["baseline_image_digest"], context="desktop-linux", memory_bytes=2 * 1024**3,
        workspace_bytes=512 * 1024**2, tmpfs_bytes=256 * 1024**2, network="none",
    )
    await backend.start({})
    try:
        await prepare_repo_runtime(backend)
        await upload_runner(backend, django=family == "django")
        args = f2p[:1]
        request = ExecutionRequest(
            argv=["/usr/local/bin/python", "-I", "-B", "/tmp/a5-runner.py"],
            stdin_bytes=json.dumps({"args": args, "labels": args, "collect_only": True, "sympy_native_helpers": family == "sympy"}).encode(),
            env={"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTHONPATH": "/workspace:/workspace/src", "A5_REPO_ROOT": "/workspace", "PYTHONDONTWRITEBYTECODE": "1"},
            deadline_mono=time.monotonic() + 180,
            quotas=OutputQuotas(memory_per_stream_bytes=4 * 1024**2, artifact_per_tool_bytes=16 * 1024**2),
        )
        execution = await backend.execute(request)
        print("exec", execution.status.value, execution.exit_code)
        print("stderr", (execution.stderr.text_preview or "")[-400:])
        raw = await backend._ok(
            "exec", backend.name, "/usr/local/bin/python", "-I", "-S", "-c",
            "from pathlib import Path; import sys; p=Path('/tmp/a5-pytest-receipt.json'); sys.stdout.buffer.write(p.read_bytes())",
            limit=8 * 1024**2,
        )
        data = json.loads(raw)
        print("collected", len(data.get("collected") or []))
        print("sample", (data.get("collected") or ["none"])[:3])
        print("expect", f2p[0])
        print("errors", str((data.get("collection_errors") or [""])[:1])[:300])
        print("runner_error", data.get("runner_error"))
    finally:
        await backend.close()


if __name__ == "__main__":
    asyncio.run(main())
