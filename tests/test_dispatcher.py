import asyncio
import json
import os

import pytest

from src.execution.base import (CleanupState, ExecutionResult, ExecutionStatus,
                                StreamCapture)
from src.execution.docker import DockerExecutionBackend
from src.policy.dispatcher import DispatcherError, ReadSearchDispatcher
from src.runtime.deadline import DeadlineClock
from src.runtime.hooks import HookContext
from src.runtime.window import WindowPolicy, WindowPolicyHooks
from src.runtime.recovery import reduce_events


class FakeBackend:
    profile = "docker_linux"
    capabilities = {"profile": "docker_linux", "filesystem_isolation": True}

    def __init__(self):
        self.requests = []

    async def execute(self, request):
        self.requests.append(request)
        payload = json.loads(request.stdin_bytes)
        body = {"path": payload.get("path"), "content": "VALUE=7\n", "kind": "file"}
        raw = json.dumps(body, separators=(",", ":"))
        return ExecutionResult(
            status=ExecutionStatus.SUCCEEDED,
            stdout=StreamCapture(text_preview=raw),
            cleanup_state=CleanupState.CLEANED,
            bytes_seen=len(raw),
        )


def test_dispatcher_rejects_unsafe_proposals():
    dispatcher = ReadSearchDispatcher(FakeBackend())
    with pytest.raises(DispatcherError):
        dispatcher._validate({"proposal_id": "x", "tool": "run", "argv": []})
    with pytest.raises(DispatcherError):
        dispatcher._validate({"proposal_id": "x", "tool": "read", "path": "../secret"})


def test_dispatcher_returns_hashed_receipt():
    backend = FakeBackend()
    receipt = asyncio.run(ReadSearchDispatcher(backend).dispatch(
        {"proposal_id": "x", "tool": "read", "path": "settings.py"},
        deadline_mono=None, cancel_event=None, run_meter=None))
    assert receipt["success"] is True
    assert receipt["output_sha256"] == receipt["observation_sha256"]
    assert backend.requests[0].argv[:3] == ["/usr/local/bin/python", "-I", "-S"]


class ProposalPlugin:
    name = "fixture-proposal"
    schema_version = "0.1"

    async def decide(self, policy_input):
        return {
            "schema_version": "0.1", "candidates": [], "events": [],
            "state": {"calls": 1},
            "action_proposals": [{"proposal_id": "x", "tool": "read", "path": "settings.py"}],
        }


def test_window_executes_and_injects_dispatch_observation():
    backend = FakeBackend()
    hooks = WindowPolicyHooks(WindowPolicy(dispatcher="read_search", dispatcher_max_calls=1),
                              ProposalPlugin(), dispatcher=ReadSearchDispatcher(backend))
    ctx = HookContext(extra={"deadline": DeadlineClock()})
    view = asyncio.run(hooks.before_llm([{"role": "user", "content": "task"}], ctx))
    assert view[-1]["role"] == "user"
    assert "VALUE=7" in view[-1]["content"]
    assert ctx.extra["context_stats"]["plugin"]["action_proposals"][0]["status"] == "executed"


def test_dispatch_receipt_replays_as_h4_manager_state():
    receipt = {"operation_id": "h5-dispatch-1", "attempt_id": "a1",
               "observation_sha256": "abc", "success": True}
    state = reduce_events([
        {"seq": 1, "event_type": "run.started", "payload": {}},
        {"seq": 2, "event_type": "plugin.dispatch",
         "payload": {"receipt": receipt,
                      "manager_state": {"schema_version": "0.1", "summary_calls": 0,
                                         "summaries": [], "plugin_state": {"calls": 1},
                                         "dispatch_calls": 1, "dispatch_receipts": [receipt],
                                         "dispatch_observations": [{"role": "tool", "sha256": "abc"}]}}},
    ])
    assert state.plugin_state["h4"]["dispatch_calls"] == 1
    assert state.plugin_state["h4"]["plugin_state"]["calls"] == 1


@pytest.mark.skipif(os.environ.get("HARNESS_DOCKER_TESTS") != "1",
                    reason="opt in: requires Docker Desktop")
def test_dispatcher_executes_inside_pinned_docker_image():
    async def run():
        backend = DockerExecutionBackend(
            image="python@sha256:2f17fc044b579bab302c2e8054d3a686e2cb9a83de48e70534b94cd8ebbe06a9",
            context=os.environ.get("HARNESS_DOCKER_CONTEXT", "desktop-linux"),
        )
        await backend.start({"settings.py": b"VALUE=7\n"})
        try:
            receipt = await ReadSearchDispatcher(backend).dispatch(
                {"proposal_id": "docker", "tool": "read", "path": "settings.py"},
                deadline_mono=None, cancel_event=None, run_meter=None)
            assert receipt["success"] is True
            assert "VALUE=7" in receipt["output"]
        finally:
            await backend.close()

    asyncio.run(run())
