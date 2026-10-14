"""Budget: step/time limits + optional shared model ledger (HP-03).

English: step count, wall-clock run/step timeouts, and optional ModelBudgetLedger.
"""

from __future__ import annotations

import time

from src.policy.model_budget import ModelBudgetLedger


class BudgetExhausted(Exception):
    def __init__(self, reason: str, *, kind: str = "budget_exhausted"):
        self.reason = reason
        self.kind = kind
        super().__init__(reason)


class Budget:
    def __init__(
        self,
        max_steps: int = 30,
        total_timeout_seconds: float = 600.0,
        step_timeout_seconds: float = 120.0,
        model_ledger: ModelBudgetLedger | None = None,
    ):
        self.max_steps = max_steps
        self.total_timeout_seconds = total_timeout_seconds
        self.step_timeout_seconds = step_timeout_seconds
        self.model_ledger = model_ledger

        self._step_count = 0
        self._start_time: float | None = None
        self._last_step_start: float | None = None
        self._run_deadline_mono: float | None = None

    def start(self) -> None:
        self._start_time = time.monotonic()
        self._step_count = 0
        self._run_deadline_mono = self._start_time + max(0.0, self.total_timeout_seconds)

    @property
    def run_deadline_mono(self) -> float | None:
        return self._run_deadline_mono

    def start_step(self) -> None:
        self._step_count += 1
        self._last_step_start = time.monotonic()

        if self._step_count > self.max_steps:
            raise BudgetExhausted(
                f"Step limit exceeded: {self._step_count}/{self.max_steps}",
                kind="step_limit",
            )

        if self._run_deadline_mono is not None:
            now = time.monotonic()
            if now >= self._run_deadline_mono:
                elapsed = now - (self._start_time or now)
                raise BudgetExhausted(
                    f"Total timeout exceeded: {elapsed:.1f}s / {self.total_timeout_seconds}s",
                    kind="run_deadline",
                )

    def check_step_timeout(self) -> None:
        if self._last_step_start is not None:
            elapsed = time.monotonic() - self._last_step_start
            if elapsed > self.step_timeout_seconds:
                raise BudgetExhausted(
                    f"Step timeout exceeded: {elapsed:.1f}s / {self.step_timeout_seconds}s",
                    kind="step_deadline",
                )

    def step_deadline_mono(self) -> float | None:
        if self._last_step_start is None:
            return None
        return self._last_step_start + max(0.0, self.step_timeout_seconds)

    @property
    def step_count(self) -> int:
        return self._step_count

    @property
    def elapsed(self) -> float:
        if self._start_time is None:
            return 0.0
        return time.monotonic() - self._start_time

    def summary(self) -> dict:
        out = {
            "steps": self._step_count,
            "max_steps": self.max_steps,
            "elapsed_s": round(self.elapsed, 2),
            "total_timeout_s": self.total_timeout_seconds,
        }
        if self.model_ledger is not None:
            out["model_ledger"] = self.model_ledger.snapshot()
        return out
