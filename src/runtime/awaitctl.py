"""Race an awaitable against cancel + monotonic deadline (HP-03).

Cancels the work task on stop and waits a bounded cleanup grace — does not
only check loop boundaries.
"""

from __future__ import annotations

import asyncio
import logging
import inspect
import time
from typing import Any, Awaitable, TypeVar

from src.runtime.deadline import (
    CLEANUP_GRACE_S,
    DeadlineClock,
    DeadlineExceeded,
    TerminationKind,
    UserCancelled,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CleanupFailed(DeadlineExceeded):
    """Work may still be running; callers must stop all further side effects."""

    def __init__(self, elapsed_s: float):
        super().__init__(TerminationKind.CLEANUP_FAILED, "work cleanup could not be confirmed")
        self.elapsed_s = elapsed_s


async def await_with_control(
    awaitable: Awaitable[T],
    *,
    deadline: DeadlineClock | None = None,
    cancel_event: asyncio.Event | None = None,
    cleanup_grace_s: float = CLEANUP_GRACE_S,
) -> T:
    """Wait for *awaitable* until it completes, or cancel/deadline fires.

    On cancel/deadline: cancel the work task, wait up to ``cleanup_grace_s`` for
    it to finish (so tool/HTTP finally blocks can run), then raise
    ``UserCancelled`` / ``DeadlineExceeded``. Never returns a successful result
    after stop has been requested.
    """
    def check_stop() -> None:
        if cancel_event is not None and cancel_event.is_set():
            raise UserCancelled("user cancelled")
        if deadline is not None:
            deadline.raise_if_expired_or_cancelled()

    try:
        check_stop()
    except BaseException:
        if inspect.iscoroutine(awaitable):
            awaitable.close()
        raise
    work = asyncio.ensure_future(awaitable)
    try:
        while True:
            check_stop()
            if work.done():
                return work.result()
            remaining = deadline.remaining_or_zero() if deadline else float("inf")
            await asyncio.wait({work}, timeout=min(0.02, remaining))
    except (UserCancelled, DeadlineExceeded, asyncio.CancelledError) as stop:
        started = time.monotonic()
        if not work.done():
            work.cancel()
            # wait_for waits for cancellation acknowledgement and can hang forever.
            # asyncio.wait imposes a true bound without cancelling cleanup again.
            await asyncio.wait({work}, timeout=max(0, cleanup_grace_s))
        if not work.done():
            work.add_done_callback(lambda t: t.exception() if not t.cancelled() else None)
            raise CleanupFailed(time.monotonic() - started) from stop
        if not work.cancelled():
            error = work.exception()
            if error is not None:
                raise CleanupFailed(time.monotonic() - started) from error
            result = work.result()
            if getattr(result, "error_kind", None) == "cleanup_failed":
                failed = CleanupFailed(time.monotonic() - started)
                failed.work_result = result
                raise failed from stop
            # Preserve structured partial output for the tool caller.
            stop.work_result = result
        raise


def estimate_input_tokens(
    messages: list[dict[str, Any]] | None,
    tools: list[dict[str, Any]] | None = None,
) -> tuple[int, str]:
    """Estimate prompt tokens from serialized messages + tool schemas.

    Method ``chars_div_4_json``: UTF-8 JSON byte length / 4, minimum 1.
    This is an estimate — never claimed as provider-accurate metering.
    """
    import json

    try:
        payload = json.dumps(
            {"messages": messages or [], "tools": tools or []},
            ensure_ascii=False,
            default=str,
        )
    except Exception:
        payload = str(messages) + str(tools)
    n = max(1, len(payload.encode("utf-8")) // 4)
    return n, "chars_div_4_json"
