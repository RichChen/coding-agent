"""Budget：步数上限、总耗时、单步耗时（后续可扩展 token/费用）。

English: step count, wall-clock total timeout, per-step timeout guard.
"""

from __future__ import annotations

import time


class BudgetExhausted(Exception):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


class Budget:
    def __init__(
        self,
        max_steps: int = 30,
        total_timeout_seconds: float = 600.0,
        step_timeout_seconds: float = 120.0,
    ):
        self.max_steps = max_steps
        self.total_timeout_seconds = total_timeout_seconds
        self.step_timeout_seconds = step_timeout_seconds

        self._step_count = 0
        self._start_time: float | None = None
        self._last_step_start: float | None = None

    def start(self) -> None:
        self._start_time = time.monotonic()
        self._step_count = 0

    def start_step(self) -> None:
        self._step_count += 1
        self._last_step_start = time.monotonic()

        if self._step_count > self.max_steps:
            raise BudgetExhausted(
                f"Step limit exceeded: {self._step_count}/{self.max_steps}"
            )

        if self._start_time is not None:
            elapsed = time.monotonic() - self._start_time
            if elapsed > self.total_timeout_seconds:
                raise BudgetExhausted(
                    f"Total timeout exceeded: {elapsed:.1f}s / {self.total_timeout_seconds}s"
                )

    def check_step_timeout(self) -> None:
        if self._last_step_start is not None:
            elapsed = time.monotonic() - self._last_step_start
            if elapsed > self.step_timeout_seconds:
                raise BudgetExhausted(
                    f"Step timeout exceeded: {elapsed:.1f}s / {self.step_timeout_seconds}s"
                )

    @property
    def step_count(self) -> int:
        return self._step_count

    @property
    def elapsed(self) -> float:
        if self._start_time is None:
            return 0.0
        return time.monotonic() - self._start_time

    def summary(self) -> dict:
        return {
            "steps": self._step_count,
            "max_steps": self.max_steps,
            "elapsed_s": round(self.elapsed, 2),
            "total_timeout_s": self.total_timeout_seconds,
        }
