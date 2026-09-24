"""Platform acceptance cases; a Windows skip is explicitly not Linux evidence."""
import asyncio
import json
import os
import shlex
import signal
import sys
import time
from pathlib import Path

import pytest

from src.execution.base import ExecutionRequest
from src.execution.local import LocalExecutionBackend, build_minimal_env


pytestmark = pytest.mark.skipif(not sys.platform.startswith("linux"), reason="requires real Linux process groups")


@pytest.mark.asyncio
@pytest.mark.parametrize("shell", [False, True])
@pytest.mark.parametrize("scenario", ["cancel", "ignore_term_timeout", "leader_exits"])
async def test_process_group_children_stop(tmp_path, shell, scenario):
    marker, pids, ready = tmp_path / "marker", tmp_path / "pids", tmp_path / "ready"
    script = tmp_path / "fixture.py"
    script.write_text('''
import json, os, signal, sys, time
from pathlib import Path
base = Path(sys.argv[1])
ignore = sys.argv[2] == "ignore_term_timeout"
if ignore: signal.signal(signal.SIGTERM, signal.SIG_IGN)
leader = os.getpid()
child = os.fork()
if child == 0:
    grandchild = os.fork()
    if grandchild == 0:
        (base / "pids").write_text(json.dumps([leader, os.getppid(), os.getpid()]))
        (base / "marker").write_bytes(b"x")
        (base / "ready").touch()
        while True:
            with open(base / "marker", "ab") as stream: stream.write(b"x")
            time.sleep(.1)
    while True: time.sleep(.1)
while not (base / "ready").exists(): time.sleep(.01)
if sys.argv[2] == "leader_exits": sys.exit(0)
while True: time.sleep(.1)
''', encoding="utf-8")
    cancel = asyncio.Event()
    argv = [sys.executable, str(script), str(tmp_path), scenario]
    request = ExecutionRequest(argv=None if shell else argv,
        shell_command=shlex.join(argv) if shell else None, cwd=tmp_path,
        env=build_minimal_env([]), cancel_event=cancel,
        deadline_mono=time.monotonic() + (2 if scenario == "ignore_term_timeout" else 10))
    task = asyncio.create_task(LocalExecutionBackend("controlled").execute(request))
    captured = []
    try:
        limit = time.monotonic() + 5
        while not ready.exists():
            assert time.monotonic() < limit, "child did not become ready"
            await asyncio.sleep(.02)
        captured = json.loads(pids.read_text())
        if scenario == "cancel":
            cancel.set()
        result = await asyncio.wait_for(task, timeout=14)
        baseline = marker.stat().st_size
        await asyncio.sleep(3)
        assert marker.stat().st_size == baseline, "marker grew AFTER cleanup returned"
        for pid in captured:
            stat = Path(f"/proc/{pid}/stat")
            if stat.exists():
                assert stat.read_text().split(")", 1)[1].split()[0] == "Z", f"live child {pid}"
        assert result.cleanup_state.value == "cleaned"
    finally:
        cancel.set()
        # Only kill PIDs created by this fixture; no group escape is attempted.
        if pids.exists() and not captured:
            captured = json.loads(pids.read_text())
        for pid in captured:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        if not task.done():
            task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass
