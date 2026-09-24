"""HP-03 patch: in-flight await control, per-attempt budget, termination gates."""

from __future__ import annotations

import asyncio
import time

import httpx
import pytest

from src.llm.client import LLMClient, LLMError, LLMErrorKind, LLMResponse, ToolCall
from src.policy.budget import Budget
from src.policy.model_budget import ModelBudgetLedger
from src.policy.sandbox import Sandbox
from src.runtime.awaitctl import await_with_control
from src.runtime.deadline import DeadlineClock, DeadlineExceeded, UserCancelled
from src.runtime.loop import AgentLoop, FailureReason
from src.runtime.retry import RetryConfig, RetryPolicy
from src.tools.base import SideEffectClass, Tool, ToolContext, ToolResult, ToolStatus
from src.tools.registry import ToolRegistry
from tests.fixtures.mock_llm import MockLLMClient


class SleepOnlyTool(Tool):
    """Does NOT poll cancel — host must interrupt via await_with_control."""

    name = "sleep_only"
    description = "sleep without polling"
    side_effect = SideEffectClass.READ_ONLY
    parameters = {
        "type": "object",
        "properties": {"seconds": {"type": "number"}},
        "required": ["seconds"],
        "additionalProperties": False,
    }
    started = 0

    async def execute(self, params: dict, ctx: ToolContext) -> ToolResult:
        type(self).started += 1
        await asyncio.sleep(float(params.get("seconds", 5)))
        return ToolResult(call_id=ctx.call_id, name=self.name, success=True, output="slept")


class CountingWrite(Tool):
    name = "write_file"
    description = "count"
    side_effect = SideEffectClass.IDEMPOTENT_WRITE
    parameters = {
        "type": "object",
        "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
        "required": ["path", "content"],
        "additionalProperties": False,
    }

    def __init__(self) -> None:
        self.calls = 0

    async def execute(self, params: dict, ctx: ToolContext) -> ToolResult:
        self.calls += 1
        return ToolResult(
            call_id=ctx.call_id, name=self.name, success=True, output="wrote"
        )


class CleanupFailedTool(Tool):
    name = "cleanup_fail"
    description = "returns outcome_unknown"
    side_effect = SideEffectClass.NON_IDEMPOTENT
    parameters = {"type": "object", "properties": {}, "additionalProperties": False}

    async def execute(self, params: dict, ctx: ToolContext) -> ToolResult:
        return ToolResult(
            call_id=ctx.call_id,
            name=self.name,
            success=False,
            output="partial",
            error="cleanup could not be confirmed",
            status=ToolStatus.OUTCOME_UNKNOWN,
            error_kind="cleanup_failed",
            cleanup_state="cleanup_failed",
            cleanup_elapsed_s=2.1,
        )


class SlowLLM:
    """Non-streaming LLM that sleeps inside chat — must be interruptible."""

    def __init__(self, sleep_s: float = 0.25, text: str = "late"):
        self.sleep_s = sleep_s
        self.text = text
        self.calls = 0
        self.model = "slow"
        self.max_tokens = 16
        self._owns_http_client = False

    @property
    def owns_http_client(self) -> bool:
        return False

    async def chat(self, messages, tools=None):
        self.calls += 1
        await asyncio.sleep(self.sleep_s)
        return LLMResponse(
            text=self.text,
            usage={"total_tokens": 1, "provenance": "provider"},
        )

    async def stream_chat(self, messages, tools=None):
        raise RuntimeError("not used")

    async def aclose(self):
        return None


@pytest.mark.asyncio
async def test_run_deadline_interrupts_model_await_not_success(tmp_path):
    llm = SlowLLM(sleep_s=0.25)
    agent = AgentLoop(
        llm=llm,  # type: ignore[arg-type]
        tools=ToolRegistry(),
        sandbox=Sandbox(workspace_root=tmp_path),
        budget=Budget(max_steps=3, total_timeout_seconds=0.04, step_timeout_seconds=30),
        enabled_tools=[],
        retry_config=RetryConfig(max_retries=0),
    )
    t0 = time.monotonic()
    result = await agent.run("deadline vs sleep", task_id="dl-model")
    elapsed = time.monotonic() - t0
    assert result.success is False
    assert result.failure_reason == FailureReason.RUN_DEADLINE
    assert elapsed < 0.2  # must not wait for full 0.25s sleep
    assert llm.calls >= 1


@pytest.mark.asyncio
async def test_cancel_during_model_await_not_success(tmp_path):
    llm = SlowLLM(sleep_s=1.0)
    cancel = asyncio.Event()
    agent = AgentLoop(
        llm=llm,  # type: ignore[arg-type]
        tools=ToolRegistry(),
        sandbox=Sandbox(workspace_root=tmp_path),
        budget=Budget(max_steps=3, total_timeout_seconds=30, step_timeout_seconds=30),
        enabled_tools=[],
        cancel_event=cancel,
        retry_config=RetryConfig(max_retries=0),
    )

    async def flip():
        await asyncio.sleep(0.05)
        cancel.set()

    asyncio.create_task(flip())
    t0 = time.monotonic()
    result = await agent.run("cancel mid model", task_id="cancel-model")
    assert result.success is False
    assert result.failure_reason in (
        FailureReason.USER_CANCELLED,
        FailureReason.CANCELLED,
    )
    assert time.monotonic() - t0 < 0.5


@pytest.mark.asyncio
async def test_host_interrupts_sleep_only_tool_no_polling(tmp_path):
    SleepOnlyTool.started = 0
    cancel = asyncio.Event()
    writer = CountingWrite()
    tools = ToolRegistry()
    tools.register(SleepOnlyTool())
    tools.register(writer)
    llm = MockLLMClient(
        [
            LLMResponse(
                tool_calls=[
                    ToolCall(id="s1", name="sleep_only", arguments={"seconds": 5}),
                    ToolCall(
                        id="w1",
                        name="write_file",
                        arguments={"path": "x.txt", "content": "no"},
                    ),
                ],
                usage={"total_tokens": 1, "provenance": "provider"},
            )
        ]
    )
    agent = AgentLoop(
        llm=llm,
        tools=tools,
        sandbox=Sandbox(workspace_root=tmp_path),
        budget=Budget(max_steps=5, total_timeout_seconds=30, step_timeout_seconds=20),
        enabled_tools=["sleep_only", "write_file"],
        cancel_event=cancel,
        retry_config=RetryConfig(max_retries=0),
    )

    async def flip():
        await asyncio.sleep(0.1)
        cancel.set()

    asyncio.create_task(flip())
    result = await agent.run("interrupt sleep", task_id="sleep-cancel")
    assert result.success is False
    assert writer.calls == 0
    assert SleepOnlyTool.started == 1


@pytest.mark.asyncio
async def test_cleanup_failed_blocks_subsequent_write_and_model(tmp_path):
    writer = CountingWrite()
    tools = ToolRegistry()
    tools.register(CleanupFailedTool())
    tools.register(writer)
    llm = MockLLMClient(
        [
            LLMResponse(
                tool_calls=[
                    ToolCall(id="c1", name="cleanup_fail", arguments={}),
                    ToolCall(
                        id="w1",
                        name="write_file",
                        arguments={"path": "a.txt", "content": "x"},
                    ),
                ],
                usage={"total_tokens": 1, "provenance": "provider"},
            ),
            LLMResponse(text="should not happen", usage={"total_tokens": 1, "provenance": "provider"}),
        ]
    )
    agent = AgentLoop(
        llm=llm,
        tools=tools,
        sandbox=Sandbox(workspace_root=tmp_path),
        budget=Budget(max_steps=5, total_timeout_seconds=30, step_timeout_seconds=20),
        enabled_tools=["cleanup_fail", "write_file"],
        retry_config=RetryConfig(max_retries=0),
    )
    result = await agent.run("cleanup gate", task_id="cleanup-gate")
    assert result.success is False
    assert result.failure_reason == FailureReason.CLEANUP_FAILED
    assert writer.calls == 0
    assert llm._call_count == 1  # no second model request


@pytest.mark.asyncio
async def test_retry_reserves_each_attempt_max_calls(tmp_path):
    """max_model_calls=1 must block the second HTTP attempt after 429."""
    ledger = ModelBudgetLedger(max_model_calls=1)
    calls = {"n": 0}

    async def flaky_chat(messages, tools=None):
        calls["n"] += 1
        raise LLMError("rate limited", kind=LLMErrorKind.HTTP, status_code=429)

    clock = DeadlineClock()
    clock.set_run(30.0)
    policy = RetryPolicy(
        RetryConfig(max_retries=3, backoff_base_seconds=0.01, retry_on=["http"]),
        deadline=clock,
        model_ledger=ledger,
    )
    with pytest.raises(Exception):
        await policy.execute(
            flaky_chat,
            [{"role": "user", "content": "hi"}],
            None,
            messages=[{"role": "user", "content": "hi"}],
            tools=None,
            max_output_tokens=10,
        )
    # First attempt reserved (calls_started=1); second reserve must fail before call.
    assert ledger.calls_started == 1
    assert calls["n"] == 1
    assert ledger.settlements
    assert ledger.settlements[0].provenance == "unknown"


@pytest.mark.asyncio
async def test_cost_without_split_keeps_conservative_reserve():
    ledger = ModelBudgetLedger(
        max_cost_usd=5.0,
        price_table={"prompt_per_1k": 1.0, "completion_per_1k": 1.0},
    )
    res = ledger.reserve(estimated_input_tokens=1000, max_output_tokens=1000)
    assert res.reserved_cost_usd == pytest.approx(2.0)
    settlement = ledger.settle(
        res.reservation_id,
        {"total_tokens": 100, "provenance": "provider"},  # missing split
    )
    assert settlement.cost_provenance == "conservative_reserve"
    assert settlement.cost_usd == pytest.approx(2.0)
    assert ledger.cost_committed == pytest.approx(2.0)  # not released to 0


@pytest.mark.asyncio
async def test_await_with_control_deadline():
    async def slow():
        await asyncio.sleep(1.0)
        return "ok"

    clock = DeadlineClock()
    clock.set_run(0.05)
    with pytest.raises(DeadlineExceeded):
        await await_with_control(slow(), deadline=clock)
