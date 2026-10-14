import asyncio

import pytest

from src.execution.base import ExecutionRequest
from src.execution.local import LocalExecutionBackend


@pytest.mark.asyncio
async def test_cancel_while_spawn_acquires_handle_then_cleans(monkeypatch):
    started, release = asyncio.Event(), asyncio.Event()

    class Process:
        pid = 123
        returncode = None
        stdout = stderr = stdin = None
        def terminate(self):
            self.returncode = -15
        def kill(self):
            self.returncode = -9
        async def wait(self):
            return self.returncode

    proc = Process()
    async def spawn(*args, **kwargs):
        started.set()
        await release.wait()
        return proc
    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    task = asyncio.create_task(LocalExecutionBackend("legacy_host").execute(ExecutionRequest(argv=["fixture"])))
    await started.wait()
    task.cancel()
    release.set()
    result = await task
    assert proc.returncode == -15
    assert result.status.value == "cancelled"
    assert result.cleanup_state.value == "cleaned"
