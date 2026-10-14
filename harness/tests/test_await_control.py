import asyncio
import time

import pytest

from src.runtime.awaitctl import CleanupFailed, await_with_control
from src.runtime.deadline import UserCancelled
from src.policy.model_budget import BudgetLedgerError, ModelBudgetLedger
from src.tools.base import ToolResult, ToolStatus


@pytest.mark.asyncio
async def test_cleanup_resisting_cancel_has_real_bound():
    started, release, cancel = asyncio.Event(), asyncio.Event(), asyncio.Event()

    async def resistant():
        started.set()
        try:
            await asyncio.Future()
        except asyncio.CancelledError:
            await release.wait()

    work = asyncio.create_task(resistant())
    await started.wait()
    runner = asyncio.create_task(await_with_control(work, cancel_event=cancel, cleanup_grace_s=.05))
    await asyncio.sleep(0)
    before = time.monotonic()
    cancel.set()
    try:
        with pytest.raises(CleanupFailed):
            await asyncio.wait_for(runner, 1)
        assert time.monotonic() - before < .5
    finally:
        release.set()
        await work


@pytest.mark.asyncio
async def test_partial_result_survives_cancellation():
    cancel, started = asyncio.Event(), asyncio.Event()

    async def work():
        started.set()
        try:
            await asyncio.Future()
        except asyncio.CancelledError:
            return ToolResult("c", "command", False, "partial stdout", status=ToolStatus.CANCELLED)

    runner = asyncio.create_task(await_with_control(work(), cancel_event=cancel))
    await started.wait()
    cancel.set()
    with pytest.raises(UserCancelled) as exc:
        await runner
    assert exc.value.work_result.output == "partial stdout"


@pytest.mark.asyncio
async def test_stop_beats_success_and_preclosed_coroutine():
    cancel = asyncio.Event()

    async def work():
        cancel.set()
        return "success"

    with pytest.raises(UserCancelled):
        await await_with_control(work(), cancel_event=cancel)
    coro = work()
    with pytest.raises(UserCancelled):
        await await_with_control(coro, cancel_event=cancel)
    assert coro.cr_frame is None


@pytest.mark.parametrize("value", [-.5, .5, float("nan"), float("inf"), True])
def test_invalid_budget_and_usage_never_free(value):
    with pytest.raises(BudgetLedgerError):
        ModelBudgetLedger(max_tokens=value)
    ledger = ModelBudgetLedger(max_tokens=100)
    r = ledger.reserve(estimated_input_tokens=10, max_output_tokens=20)
    ledger.settle(r.reservation_id, {"total_tokens": value, "provenance": "provider"})
    assert ledger.tokens_committed == 30
