import asyncio
import dataclasses
import subprocess
import sys
import time
from pathlib import Path

import pytest

from src.runtime.session import RunSession, compatibility
from src.tracing.store import EventStore, StoreError, canonical
from tests.fixtures.recovery_worker import expected, make_loop


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.asyncio
@pytest.mark.parametrize("window", ["before_intent", "after_intent", "after_effect", "after_result"])
@pytest.mark.parametrize("mode", ["append", "replace"])
async def test_real_crash_windows_no_duplicate_effects(tmp_path, window, mode):
    workspace, run = tmp_path / "workspace", tmp_path / "run"
    workspace.mkdir()
    if mode == "replace":
        (workspace / "value.txt").write_text("old")
    process = subprocess.run([sys.executable, "-m", "tests.fixtures.recovery_worker", str(run), str(workspace), window, mode],
                             cwd=ROOT, capture_output=True, text=True, timeout=20)
    assert process.returncode == 71, process.stderr
    before = RunSession.replay(run)
    assert before.terminal is None
    with RunSession.resume(run, expected=expected(workspace)) as session:
        loop = make_loop(workspace, "append" if mode == "append" else "replace", resumed=True)
        result = await session.run(loop, "perform fixture write")
        confirmed = window in ("before_intent", "after_result") or (mode == "replace" and window == "after_effect")
        assert result.success == confirmed
        if not confirmed:
            assert result.termination_kind == "outcome_unknown"
            assert loop.llm._call_count == 0
        assert result.model_budget["calls_started"] == (2 if confirmed else 1)
        assert session.state.last_seq > before.last_seq
        operations = list(session.state.operations.values())
        assert len(operations) == 1
        assert operations[0]["result"]["status"] == ("succeeded" if confirmed else "outcome_unknown")
        if window == "after_result" and mode == "append":
            assert len(operations[0]["result"]["output"]) > 20000
        # A terminated run is a read, even when supplied another executable loop.
        forbidden = make_loop(workspace, "append", resumed=True)
        again = await session.run(forbidden, "perform fixture write")
        assert again.success == result.success
        assert forbidden.llm._call_count == 0
    count = (workspace / "calls.txt").read_text() if (workspace / "calls.txt").exists() else ""
    assert count == ("" if window == "after_intent" else "x")
    expected_content = ("old" if mode == "replace" else "") if window == "after_intent" else ("new" if mode == "replace" else "x")
    actual = (workspace / "value.txt").read_text() if (workspace / "value.txt").exists() else ""
    assert actual == expected_content
    replayed = RunSession.replay(run)
    assert replayed.terminal["success"] == result.success
    assert replayed.budget["calls_started"] == result.model_budget["calls_started"]
    assert b"FAKE_SECRET" not in (run / "events.sqlite3").read_bytes()


def test_resume_compatibility_expiry_workspace_and_artifacts(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    run = tmp_path / "run"
    contract = expected(workspace)
    with RunSession.create(run, task_id="t", expected=contract) as session:
        session.set_plugin_state("opaque", {"data": "x" * 20000})
    for key in ("code_id", "config_hash", "backend", "workspace", "schema_version"):
        with pytest.raises(StoreError, match=key):
            RunSession.resume(run, expected=dict(contract, **{key: "changed"}))
    artifacts = list((run / "artifacts").iterdir())
    original = artifacts[0].read_bytes()
    artifacts[0].unlink()
    with pytest.raises(StoreError, match="artifact"):
        RunSession.resume(run, expected=contract)
    artifacts[0].write_bytes(original)
    workspace.rename(tmp_path / "old-workspace")
    workspace.mkdir()
    with pytest.raises(StoreError, match="workspace"):
        RunSession.resume(run, expected=contract)


def test_pure_replay_opaque_state_and_stale_checkpoint(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    run = tmp_path / "run"
    with RunSession.create(run, task_id="t", expected=expected(workspace)) as session:
        session.checkpoint()
        session.set_plugin_state("plugin", {"opaque": [1, 2]})
        online = dataclasses.asdict(session.state)
    assert dataclasses.asdict(RunSession.replay(run)) == online


def test_competing_process_cannot_take_over_live_writer(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    run = tmp_path / "run"
    with RunSession.create(run, task_id="t", expected=expected(workspace)):
        code = "from src.tracing.store import EventStore, RunLocked; import sys;\ntry: EventStore(sys.argv[1])\nexcept RunLocked: sys.exit(73)\nsys.exit(1)"
        child = subprocess.run([sys.executable, "-c", code, str(run)], cwd=ROOT, capture_output=True, timeout=10)
        assert child.returncode == 73, child.stderr
    with RunSession.resume(run, expected=expected(workspace)):
        pass


def test_downtime_consumes_absolute_deadline(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    run = tmp_path / "run"
    with RunSession.create(run, task_id="t", expected=expected(workspace), timeout_seconds=.02):
        pass
    time.sleep(.04)
    with pytest.raises(StoreError, match="expiry"):
        RunSession.resume(run, expected=expected(workspace))
    # Offline replay remains available after expiry.
    assert RunSession.replay(run).last_seq == 1


@pytest.mark.asyncio
async def test_interrupted_model_keeps_token_call_cost_reservations(tmp_path):
    from src.policy.model_budget import ModelBudgetLedger
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    run = tmp_path / "run"
    def ledger():
        return ModelBudgetLedger(max_model_calls=1, max_tokens=50, max_cost_usd=1,
                                 price_table={"prompt_per_1k": 1, "completion_per_1k": 1})
    previous = ledger()
    previous.reserve(estimated_input_tokens=10, max_output_tokens=20)
    with RunSession.create(run, task_id="t", expected=expected(workspace)) as session:
        session.model_started(previous, "model-op", "attempt-1")
    with RunSession.resume(run, expected=expected(workspace)) as session:
        loop = make_loop(workspace, "append", resumed=True)
        loop.model_ledger = ledger()
        loop.retry.model_ledger = loop.model_ledger
        result = await session.run(loop, "task")
        assert result.termination_kind == "outcome_unknown"
        assert loop.llm._call_count == 0
        assert result.model_budget["calls_started"] == 1
        assert result.model_budget["tokens_committed"] == 30
        assert result.model_budget["cost_committed"] == pytest.approx(.03)


@pytest.mark.asyncio
async def test_masking_preserves_original_observation_in_private_store(tmp_path):
    from src.runtime.compact import MicroCompactHooks
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    run = tmp_path / "run"
    loop = make_loop(workspace, "append")
    loop.hooks = MicroCompactHooks(keep_recent=0)
    with RunSession.create(run, task_id="t", expected=expected(workspace)) as session:
        result = await session.run(loop, "perform fixture write")
        assert result.success
        observed = [m for m in loop.llm.calls[-1]["messages"] if m["role"] == "tool"]
        assert len(observed[0]["content"]) < 100
        assert len(next(iter(session.state.operations.values()))["result"]["output"]) > 20000
    replay = RunSession.replay(run)
    assert len(next(iter(replay.operations.values()))["result"]["output"]) > 20000
    # CLI replay must not even need a valid config file or credentials.
    process = subprocess.run([sys.executable, "scripts/run_single.py", "--replay", str(run), "--config", "MISSING.yaml"],
                             cwd=ROOT, capture_output=True, timeout=10)
    assert process.returncode == 0, process.stderr
    assert b'"terminated": true' in process.stdout


@pytest.mark.asyncio
async def test_command_raw_artifact_survives_observation_limit(tmp_path):
    from src.tools.command import RunCommandTool
    from src.tools.registry import ToolRegistry
    from src.policy.rules import CommandPolicy
    from src.llm.client import ToolCall, LLMResponse
    from tests.fixtures.mock_llm import MockLLMClient
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    run = tmp_path / "run"
    loop = make_loop(workspace, "append")
    loop.tools = ToolRegistry()
    loop.tools.register(RunCommandTool(command_policy=CommandPolicy(allow_all=True), execution_profile="legacy_host"))
    loop.tool_output_max_chars = 200
    loop.llm = MockLLMClient([LLMResponse(tool_calls=[ToolCall("c", "run_command", {
        "argv": [sys.executable, "-c", "print('a' * 2000)"]})]), LLMResponse(text="done")])
    with RunSession.create(run, task_id="t", expected=expected(workspace)) as session:
        result = await session.run(loop, "command")
        assert result.success
        operation = next(iter(session.state.operations.values()))
        assert len(operation["result"]["output"]) < 1000
        refs = operation["artifacts"]
        assert any(session.artifacts.read(r).startswith(b"a" * 2000) for r in refs)
        missing = session.artifacts.root / refs[0]["path"]
    missing.unlink()
    with pytest.raises(StoreError, match="artifact"):
        RunSession.replay(run)


@pytest.mark.asyncio
async def test_artifact_capacity_rejects_command_before_spawn(tmp_path):
    from src.tools.command import RunCommandTool
    from src.tools.registry import ToolRegistry
    from src.policy.rules import CommandPolicy
    from src.llm.client import ToolCall, LLMResponse
    from tests.fixtures.mock_llm import MockLLMClient
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    loop = make_loop(workspace, "append")
    loop.tools = ToolRegistry()
    loop.tools.register(RunCommandTool(command_policy=CommandPolicy(allow_all=True), execution_profile="legacy_host"))
    loop.llm = MockLLMClient([LLMResponse(tool_calls=[ToolCall("c", "run_command", {
        "argv": [sys.executable, "-c", "from pathlib import Path; Path('MUST_NOT_EXIST').touch()"]})])])
    with RunSession.create(tmp_path / "run", task_id="t", expected=expected(workspace)) as session:
        session.artifacts.limit_bytes = 1
        with pytest.raises(StoreError, match="refusing producer"):
            await session.run(loop, "quota fixture")
        assert not session.state.operations
        assert not (workspace / "MUST_NOT_EXIST").exists()
