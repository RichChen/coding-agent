"""Unified monotonic deadline + cancel control for HP-03.

English: effective deadline = min(run, step, tool/request); cancel interrupts in-flight work.
"""

from __future__ import annotations

import asyncio
import enum
import time
from dataclasses import dataclass, field


# Target wall time for cleanup convergence (seconds). Recorded separately from grace.
CLEANUP_CONVERGENCE_TARGET_S = 2.0
# Independent bounded grace for terminate→kill→wait.
CLEANUP_GRACE_S = 2.0


class TerminationKind(str, enum.Enum):
    NONE = "none"
    USER_CANCELLED = "user_cancelled"
    REQUEST_TIMEOUT = "request_timeout"
    TOOL_TIMEOUT = "tool_timeout"
    STEP_DEADLINE = "step_deadline"
    RUN_DEADLINE = "run_deadline"
    BUDGET_EXHAUSTED = "budget_exhausted"
    CLEANUP_FAILED = "cleanup_failed"
    OUTCOME_UNKNOWN = "outcome_unknown"


class DeadlineExceeded(Exception):
    def __init__(self, kind: TerminationKind, message: str = ""):
        self.kind = kind
        self.message = message or kind.value
        super().__init__(self.message)


class UserCancelled(Exception):
    """Raised when cancel_event is set and work must stop."""


@dataclass
class DeadlineClock:
    """Monotonic-clock deadline stack. Never resets the run deadline on retry."""

    run_deadline_mono: float | None = None
    step_deadline_mono: float | None = None
    tool_deadline_mono: float | None = None
    cancel_event: asyncio.Event | None = None
    cleanup_grace_s: float = CLEANUP_GRACE_S

    def set_run(self, timeout_s: float, *, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        self.run_deadline_mono = now + max(0.0, timeout_s)

    def begin_step(self, timeout_s: float, *, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        self.step_deadline_mono = now + max(0.0, timeout_s)

    def begin_tool(self, timeout_s: float | None, *, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        if timeout_s is None:
            self.tool_deadline_mono = None
            return
        self.tool_deadline_mono = now + max(0.0, timeout_s)

    def clear_tool(self) -> None:
        self.tool_deadline_mono = None

    def effective_deadline_mono(self) -> float | None:
        candidates = [
            d
            for d in (self.run_deadline_mono, self.step_deadline_mono, self.tool_deadline_mono)
            if d is not None
        ]
        return min(candidates) if candidates else None

    def remaining(self, *, now: float | None = None) -> float | None:
        deadline = self.effective_deadline_mono()
        if deadline is None:
            return None
        now = time.monotonic() if now is None else now
        return deadline - now

    def remaining_or_zero(self, *, now: float | None = None) -> float:
        rem = self.remaining(now=now)
        if rem is None:
            return float("inf")
        return max(0.0, rem)

    def which_expired(self, *, now: float | None = None) -> TerminationKind | None:
        now = time.monotonic() if now is None else now
        # Prefer the tightest / most specific reason among those already past.
        expired: list[tuple[float, TerminationKind]] = []
        if self.tool_deadline_mono is not None and now >= self.tool_deadline_mono:
            expired.append((self.tool_deadline_mono, TerminationKind.TOOL_TIMEOUT))
        if self.step_deadline_mono is not None and now >= self.step_deadline_mono:
            expired.append((self.step_deadline_mono, TerminationKind.STEP_DEADLINE))
        if self.run_deadline_mono is not None and now >= self.run_deadline_mono:
            expired.append((self.run_deadline_mono, TerminationKind.RUN_DEADLINE))
        if not expired:
            return None
        # The earliest absolute deadline among expired ones.
        expired.sort(key=lambda x: x[0])
        return expired[0][1]

    def raise_if_cancelled(self) -> None:
        if self.cancel_event is not None and self.cancel_event.is_set():
            raise UserCancelled("user cancelled")

    def raise_if_expired_or_cancelled(self, *, now: float | None = None) -> None:
        self.raise_if_cancelled()
        kind = self.which_expired(now=now)
        if kind is not None:
            raise DeadlineExceeded(kind, f"deadline exceeded: {kind.value}")

    def request_timeout_kind(self) -> TerminationKind:
        """Map effective deadline to request-level timeout when HTTP/stream is bounded."""
        kind = self.which_expired()
        if kind is not None:
            return kind
        # Soft: if tool or run is the binding constraint, prefer request_timeout label
        # only when tool/request was the min without yet expiring — caller uses TOOL/RUN.
        return TerminationKind.REQUEST_TIMEOUT


@dataclass
class CleanupReport:
    ok: bool
    elapsed_s: float
    state: str  # cleaned | cleanup_failed | skipped | not_required
    detail: str = ""
    within_convergence_target: bool = False

    def __post_init__(self) -> None:
        self.within_convergence_target = self.elapsed_s <= CLEANUP_CONVERGENCE_TARGET_S


def is_write_side_effect(side_effect) -> bool:
    """True for tools that must not start after cancel in the same batch."""
    name = getattr(side_effect, "value", str(side_effect))
    return name in ("idempotent_write", "non_idempotent")
