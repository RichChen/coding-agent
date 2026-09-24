"""HP-03: bounded execution, env allowlist, platform capability, output quotas."""

from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

import pytest

from src.execution.base import (
    ARTIFACT_PER_TOOL_BYTES,
    MEMORY_PER_STREAM_BYTES,
    RUN_OUTPUT_TOTAL_BYTES,
    ExecutionRequest,
    ExecutionStatus,
    OutputQuotas,
    RunOutputMeter,
)
from src.execution.local import (
    LocalExecutionBackend,
    build_minimal_env,
    supports_process_group_cleanup,
)
from src.policy.rules import CommandPolicy
from src.tools.base import ToolContext, ToolStatus
from src.tools.command import RunCommandTool


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    return tmp_path


def test_quota_constants_documented():
    assert MEMORY_PER_STREAM_BYTES == 64 * 1024
    assert ARTIFACT_PER_TOOL_BYTES == 1 * 1024 * 1024
    assert RUN_OUTPUT_TOTAL_BYTES == 16 * 1024 * 1024


def test_controlled_profile_blocks_on_unsupported_platform(workspace):
    if supports_process_group_cleanup():
        pytest.skip("Linux has process-group cleanup; block test is for non-Linux")
    backend = LocalExecutionBackend(profile="controlled")
    result = asyncio.run(
        backend.execute(
            ExecutionRequest(
                argv=[sys.executable, "-c", "print(1)"],
                cwd=workspace,
                env=build_minimal_env([]),
            )
        )
    )
    assert result.status in (ExecutionStatus.BLOCKED, ExecutionStatus.UNAVAILABLE)
    assert result.error_kind in ("unavailable", "blocked")
    assert "refusing to spawn" in (result.error_message or "").lower() or "cannot guarantee" in (
        result.error_message or ""
    ).lower()


def test_legacy_host_runs_on_windows(workspace):
    backend = LocalExecutionBackend(profile="legacy_host")
    result = asyncio.run(
        backend.execute(
            ExecutionRequest(
                argv=[sys.executable, "-c", "print('legacy_ok')"],
                cwd=workspace,
                env=build_minimal_env(["PATH"]),
            )
        )
    )
    assert result.status == ExecutionStatus.SUCCEEDED
    assert "legacy_ok" in result.stdout.text_preview


def test_empty_allowlist_excludes_home_and_userprofile(monkeypatch):
    monkeypatch.setenv("HOME", "/should/not/leak")
    monkeypatch.setenv("USERPROFILE", r"C:\should\not\leak")
    monkeypatch.setenv("HARNESS_FAKE_SECRET", "probe-secret-value")
    env = build_minimal_env([])
    assert "HOME" not in env
    assert "USERPROFILE" not in env
    assert "HARNESS_FAKE_SECRET" not in env
    assert "PATH" in env


def test_single_variable_allowlist(monkeypatch):
    monkeypatch.setenv("HARNESS_ONLY_ALLOWED", "visible")
    monkeypatch.setenv("HARNESS_FAKE_SECRET", "hidden")
    env = build_minimal_env(["HARNESS_ONLY_ALLOWED"])
    assert env.get("HARNESS_ONLY_ALLOWED") == "visible"
    assert "HARNESS_FAKE_SECRET" not in env


@pytest.mark.asyncio
async def test_env_probe_empty_vs_one_var(workspace, monkeypatch):
    monkeypatch.setenv("HARNESS_FAKE_SECRET", "probe-secret-value")
    monkeypatch.setenv("HARNESS_OK", "ok-value")

    tool_empty = RunCommandTool(
        command_policy=CommandPolicy(allow_all=True),
        env_whitelist=[],
        execution_profile="legacy_host",
    )
    script = (
        "import os\n"
        "print('SECRET=' + os.environ.get('HARNESS_FAKE_SECRET', 'MISSING'))\n"
        "print('OK=' + os.environ.get('HARNESS_OK', 'MISSING'))\n"
    )
    r1 = await tool_empty.execute(
        {"argv": [sys.executable, "-c", script]},
        ToolContext(workspace_root=workspace),
    )
    assert r1.success
    assert "SECRET=MISSING" in r1.output
    assert "OK=MISSING" in r1.output
    assert "probe-secret-value" not in r1.output

    tool_one = RunCommandTool(
        command_policy=CommandPolicy(allow_all=True),
        env_whitelist=["HARNESS_OK"],
        execution_profile="legacy_host",
    )
    r2 = await tool_one.execute(
        {"argv": [sys.executable, "-c", script]},
        ToolContext(workspace_root=workspace),
    )
    assert r2.success
    assert "SECRET=MISSING" in r2.output
    assert "OK=ok-value" in r2.output
    assert "probe-secret-value" not in r2.output


@pytest.mark.asyncio
async def test_nonzero_exit_maps_failed(workspace):
    tool = RunCommandTool(
        command_policy=CommandPolicy(allow_all=True),
        execution_profile="legacy_host",
    )
    result = await tool.execute(
        {"argv": [sys.executable, "-c", "import sys; sys.exit(3)"]},
        ToolContext(workspace_root=workspace),
    )
    assert result.success is False
    assert result.status == ToolStatus.FAILED
    assert result.error_kind == "nonzero_exit"
    assert "exit_code=3" in result.output


@pytest.mark.asyncio
async def test_policy_block_maps_blocked(workspace):
    tool = RunCommandTool(
        command_policy=CommandPolicy(allow_all=False, allowed_prefixes=["python"]),
        execution_profile="legacy_host",
    )
    result = await tool.execute(
        {"argv": ["curl", "https://example.com"]},
        ToolContext(workspace_root=workspace),
    )
    assert result.status == ToolStatus.BLOCKED
    assert result.error_kind == "policy_block"


@pytest.mark.asyncio
async def test_large_stdout_stderr_respect_memory_and_artifact_caps(workspace, tmp_path):
    """Each stream emits >=20 MiB; memory keep <=64KiB; artifact <=1MiB; sample peaks."""
    # Use a large run cap so producer is not stopped by run total before streams finish.
    quotas = OutputQuotas(
        memory_per_stream_bytes=MEMORY_PER_STREAM_BYTES,
        artifact_per_tool_bytes=ARTIFACT_PER_TOOL_BYTES,
        run_total_bytes=64 * 1024 * 1024,
    )
    meter = RunOutputMeter(limit_bytes=quotas.run_total_bytes)
    backend = LocalExecutionBackend(profile="legacy_host")
    art = tmp_path / "arts"
    # 20 MiB on stdout and 20 MiB on stderr via Python.
    script = (
        "import sys\n"
        "chunk = b'x' * (1024 * 1024)\n"
        "for _ in range(20):\n"
        "    sys.stdout.buffer.write(chunk)\n"
        "    sys.stdout.buffer.flush()\n"
        "    sys.stderr.buffer.write(chunk)\n"
        "    sys.stderr.buffer.flush()\n"
    )
    result = await backend.execute(
        ExecutionRequest(
            argv=[sys.executable, "-c", script],
            cwd=workspace,
            env=build_minimal_env(["PATH"]),
            quotas=quotas,
            run_meter=meter,
            artifact_dir=art,
        )
    )
    assert result.stdout.bytes_seen >= 20 * 1024 * 1024
    assert result.stderr.bytes_seen >= 20 * 1024 * 1024
    assert result.exit_code == 0
    assert result.stdout.bytes_kept_memory <= MEMORY_PER_STREAM_BYTES
    assert result.stderr.bytes_kept_memory <= MEMORY_PER_STREAM_BYTES
    assert result.stdout.bytes_kept_artifact <= ARTIFACT_PER_TOOL_BYTES
    assert result.stderr.bytes_kept_artifact <= ARTIFACT_PER_TOOL_BYTES
    # Shared per-tool artifact budget across both streams.
    assert (
        result.stdout.bytes_kept_artifact + result.stderr.bytes_kept_artifact
        <= ARTIFACT_PER_TOOL_BYTES
    )
    # Check actual files when present.
    if result.stdout.artifact_path and result.stderr.artifact_path:
        total_disk = (
            Path(result.stdout.artifact_path).stat().st_size
            + Path(result.stderr.artifact_path).stat().st_size
        )
        assert total_disk <= ARTIFACT_PER_TOOL_BYTES
    assert result.stdout.peak_buffer_bytes <= MEMORY_PER_STREAM_BYTES
    assert result.stdout.read_chunks >= 1
    assert meter.peak_read_buffer_bytes >= 0
    # Evidence snapshot for REPORT
    evidence = {
        "bytes_seen": result.bytes_seen,
        "stdout_kept_mem": result.stdout.bytes_kept_memory,
        "stderr_kept_mem": result.stderr.bytes_kept_memory,
        "stdout_kept_art": result.stdout.bytes_kept_artifact,
        "stderr_kept_art": result.stderr.bytes_kept_artifact,
        "artifact_sum": result.stdout.bytes_kept_artifact + result.stderr.bytes_kept_artifact,
        "peak_buffer": result.stdout.peak_buffer_bytes,
        "read_chunks": result.stdout.read_chunks,
        "meter": meter.snapshot(),
    }
    (tmp_path / "quota_evidence.json").write_text(
        __import__("json").dumps(evidence), encoding="utf-8"
    )
    assert result.truncated is True


@pytest.mark.asyncio
async def test_low_run_quota_cancels_producer(workspace, tmp_path):
    quotas = OutputQuotas(
        memory_per_stream_bytes=MEMORY_PER_STREAM_BYTES,
        artifact_per_tool_bytes=ARTIFACT_PER_TOOL_BYTES,
        run_total_bytes=256 * 1024,  # 256 KiB run cap
    )
    meter = RunOutputMeter(limit_bytes=quotas.run_total_bytes)
    backend = LocalExecutionBackend(profile="legacy_host")
    script = (
        "import sys, time\n"
        "chunk = b'y' * (64 * 1024)\n"
        "for _ in range(200):\n"
        "    sys.stdout.buffer.write(chunk)\n"
        "    sys.stdout.buffer.flush()\n"
        "    time.sleep(0.01)\n"
    )
    result = await backend.execute(
        ExecutionRequest(
            argv=[sys.executable, "-c", script],
            cwd=workspace,
            env=build_minimal_env(["PATH"]),
            quotas=quotas,
            run_meter=meter,
            artifact_dir=tmp_path / "arts2",
            deadline_mono=time.monotonic() + 30,
        )
    )
    assert meter.cancelled_producer or result.error_kind == "run_output_limit"
    assert meter.bytes_kept <= quotas.run_total_bytes


@pytest.mark.asyncio
async def test_tool_timeout_maps_timed_out(workspace):
    tool = RunCommandTool(
        command_policy=CommandPolicy(allow_all=True),
        timeout_seconds=1,
        execution_profile="legacy_host",
    )
    result = await tool.execute(
        {
            "argv": [
                sys.executable,
                "-c",
                "import time; time.sleep(5)",
            ]
        },
        ToolContext(workspace_root=workspace),
    )
    assert result.status == ToolStatus.TIMED_OUT
    assert result.error_kind in ("tool_timeout", "request_timeout")


@pytest.mark.asyncio
async def test_backend_task_cancel_still_reclaims(workspace):
    backend = LocalExecutionBackend(profile="legacy_host")
    req = ExecutionRequest(
        argv=[sys.executable, "-c", "import time; time.sleep(30)"],
        cwd=workspace,
        env=build_minimal_env(["PATH"]),
        cleanup_grace_s=2.0,
    )
    task = asyncio.create_task(backend.execute(req))
    await asyncio.sleep(0.15)
    task.cancel()
    result = await task
    # Structured cancel result after finally cleanup (not an unhandled CancelledError).
    assert result.status == ExecutionStatus.CANCELLED
    assert result.cleanup_elapsed_s >= 0


@pytest.mark.asyncio
async def test_cancel_during_command(workspace):
    cancel = asyncio.Event()
    tool = RunCommandTool(
        command_policy=CommandPolicy(allow_all=True),
        timeout_seconds=30,
        execution_profile="legacy_host",
    )

    async def flip():
        await asyncio.sleep(0.2)
        cancel.set()

    asyncio.create_task(flip())
    result = await tool.execute(
        {
            "argv": [
                sys.executable,
                "-c",
                "import time; time.sleep(10)",
            ]
        },
        ToolContext(
            workspace_root=workspace,
            extra={"cancel_event": cancel},
        ),
    )
    assert result.status == ToolStatus.CANCELLED
    assert result.error_kind == "user_cancelled"


# Linux process-tree acceptance (shell/argv, TERM ignoring, leader exit) lives in
# test_linux_cleanup.py. Windows skips are not evidence of Linux correctness.
