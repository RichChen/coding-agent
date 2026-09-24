"""Shared model-call / token / optional currency budget ledger (HP-03).

Reserve before each actual attempt; settle with provider usage.
Unknown / incomplete usage keeps conservative reserves — never treated as free.
"""

from __future__ import annotations

import enum
import math
from dataclasses import dataclass, field
from typing import Any


class BudgetRejectReason(str, enum.Enum):
    MAX_CALLS = "max_model_calls"
    MAX_TOKENS = "max_tokens"
    MAX_COST = "max_cost_usd"
    NO_PRICE_TABLE = "currency_limit_without_price_table"
    INSUFFICIENT_RESERVE = "insufficient_reserve"
    INVALID_CONFIG = "invalid_budget_config"


class BudgetLedgerError(Exception):
    def __init__(self, reason: BudgetRejectReason, message: str = ""):
        self.reason = reason
        self.message = message or reason.value
        super().__init__(self.message)


@dataclass
class UsageSettlement:
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    provenance: str = "unknown"  # provider | estimated | unknown
    cost_usd: float | None = None
    cost_provenance: str = "unknown"  # provider_split | conservative_reserve | unknown
    note: str | None = None


@dataclass
class Reservation:
    reservation_id: int
    reserved_tokens: int
    reserved_cost_usd: float
    estimated_input: int
    max_output: int
    estimate_method: str = "chars_div_4_json"
    settled: bool = False
    settlement: UsageSettlement | None = None


def _finite_nonneg(value: float, *, name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise BudgetLedgerError(
            BudgetRejectReason.INVALID_CONFIG,
            f"{name} must be a finite non-negative number",
        )
    f = float(value)
    if not math.isfinite(f) or f < 0:
        raise BudgetLedgerError(
            BudgetRejectReason.INVALID_CONFIG,
            f"{name} must be a finite non-negative number, got {value!r}",
        )
    return f


@dataclass
class ModelBudgetLedger:
    """Shared across parent + child agents; not reset on retry."""

    max_model_calls: int | None = None
    max_tokens: int | None = None
    max_cost_usd: float | None = None
    price_table: dict[str, float] | None = None

    calls_started: int = 0
    tokens_committed: int = 0
    cost_committed: float = 0.0
    outstanding: dict[int, Reservation] = field(default_factory=dict)
    _next_id: int = 0
    settlements: list[UsageSettlement] = field(default_factory=list)

    def __post_init__(self) -> None:
        for name in ("max_model_calls", "max_tokens"):
            value = getattr(self, name)
            if value is not None and (type(value) is not int or value < 0):
                raise BudgetLedgerError(BudgetRejectReason.INVALID_CONFIG, f"{name} must be a non-negative integer")
        if self.max_model_calls is not None and self.max_model_calls < 0:
            raise BudgetLedgerError(
                BudgetRejectReason.INVALID_CONFIG,
                "max_model_calls must be >= 0",
            )
        if self.max_tokens is not None and self.max_tokens < 0:
            raise BudgetLedgerError(
                BudgetRejectReason.INVALID_CONFIG,
                "max_tokens must be >= 0",
            )
        if self.max_cost_usd is not None:
            self.max_cost_usd = _finite_nonneg(self.max_cost_usd, name="max_cost_usd")
        if self.price_table is not None:
            self._validate_price_table(self.price_table)

    def check_can_start_paid_call(self) -> None:
        if self.max_cost_usd is not None and not self._has_price_table():
            raise BudgetLedgerError(
                BudgetRejectReason.NO_PRICE_TABLE,
                "currency hard limit set but no credible price_table; refusing to start",
            )

    def _has_price_table(self) -> bool:
        if not self.price_table:
            return False
        return (
            "prompt_per_1k" in self.price_table
            and "completion_per_1k" in self.price_table
        )

    @staticmethod
    def _validate_price_table(table: dict[str, float]) -> None:
        for key in ("prompt_per_1k", "completion_per_1k"):
            if key not in table:
                raise BudgetLedgerError(
                    BudgetRejectReason.INVALID_CONFIG,
                    f"price_table missing {key}",
                )
            _finite_nonneg(table[key], name=f"price_table.{key}")

    def _estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        assert self.price_table is not None
        return (
            prompt_tokens / 1000.0 * float(self.price_table["prompt_per_1k"])
            + completion_tokens / 1000.0 * float(self.price_table["completion_per_1k"])
        )

    def reserve(
        self,
        *,
        estimated_input_tokens: int,
        max_output_tokens: int,
        estimate_method: str = "chars_div_4_json",
    ) -> Reservation:
        self.check_can_start_paid_call()
        if any(type(v) is not int or v < 0 for v in (estimated_input_tokens, max_output_tokens)):
            raise BudgetLedgerError(
                BudgetRejectReason.INVALID_CONFIG,
                "estimated_input_tokens and max_output_tokens must be >= 0",
            )
        if self.max_model_calls is not None and self.calls_started >= self.max_model_calls:
            raise BudgetLedgerError(
                BudgetRejectReason.MAX_CALLS,
                f"model call limit reached: {self.calls_started}/{self.max_model_calls}",
            )

        need_tokens = int(estimated_input_tokens) + int(max_output_tokens)
        need_cost = 0.0
        if self.max_cost_usd is not None:
            need_cost = self._estimate_cost(estimated_input_tokens, max_output_tokens)

        if self.max_tokens is not None and self.tokens_committed + need_tokens > self.max_tokens:
            raise BudgetLedgerError(
                BudgetRejectReason.INSUFFICIENT_RESERVE,
                (
                    f"token reserve would exceed limit: "
                    f"{self.tokens_committed}+{need_tokens}>{self.max_tokens}"
                ),
            )
        if self.max_cost_usd is not None and self.cost_committed + need_cost > self.max_cost_usd:
            raise BudgetLedgerError(
                BudgetRejectReason.INSUFFICIENT_RESERVE,
                (
                    f"cost reserve would exceed limit: "
                    f"{self.cost_committed}+{need_cost}>{self.max_cost_usd}"
                ),
            )

        self._next_id += 1
        res = Reservation(
            reservation_id=self._next_id,
            reserved_tokens=need_tokens,
            reserved_cost_usd=need_cost,
            estimated_input=estimated_input_tokens,
            max_output=max_output_tokens,
            estimate_method=estimate_method,
        )
        self.outstanding[res.reservation_id] = res
        self.calls_started += 1
        self.tokens_committed += need_tokens
        self.cost_committed += need_cost
        return res

    def settle(self, reservation_id: int, usage: dict[str, Any] | None) -> UsageSettlement:
        res = self.outstanding.get(reservation_id)
        if res is None:
            raise KeyError(f"unknown reservation {reservation_id}")

        settlement = self._parse_usage(usage)
        token_ok = (
            settlement.provenance == "provider"
            and isinstance(settlement.total_tokens, int)
            and settlement.total_tokens >= 0
        )
        split_ok = (
            isinstance(settlement.prompt_tokens, int)
            and settlement.prompt_tokens >= 0
            and isinstance(settlement.completion_tokens, int)
            and settlement.completion_tokens >= 0
        )

        if token_ok:
            self.tokens_committed -= res.reserved_tokens
            self.tokens_committed += settlement.total_tokens
        # else: keep conservative token reserve

        if self.max_cost_usd is not None and self._has_price_table():
            if token_ok and split_ok:
                actual_cost = self._estimate_cost(
                    settlement.prompt_tokens or 0,
                    settlement.completion_tokens or 0,
                )
                settlement.cost_usd = actual_cost
                settlement.cost_provenance = "provider_split"
                self.cost_committed -= res.reserved_cost_usd
                self.cost_committed += actual_cost
            else:
                # Missing prompt/completion split: do NOT treat as free.
                # Keep reserved cost; mark cost unknown/conservative.
                settlement.cost_usd = res.reserved_cost_usd
                settlement.cost_provenance = "conservative_reserve"
                settlement.provenance = (
                    settlement.provenance if token_ok else "unknown"
                )
                settlement.note = (
                    (settlement.note + "; " if settlement.note else "")
                    + "cost kept at conservative reserve (missing prompt/completion split)"
                )
        elif not token_ok:
            settlement.provenance = "unknown"

        res.settled = True
        res.settlement = settlement
        self.settlements.append(settlement)
        del self.outstanding[reservation_id]
        return settlement

    def settle_unknown(self, reservation_id: int, *, reason: str = "interrupted") -> UsageSettlement:
        return self.settle(
            reservation_id,
            {
                "prompt_tokens": None,
                "completion_tokens": None,
                "total_tokens": None,
                "provenance": "unknown",
                "note": reason,
            },
        )

    @staticmethod
    def _parse_usage(usage: dict[str, Any] | None) -> UsageSettlement:
        if not isinstance(usage, dict):
            return UsageSettlement(provenance="unknown")
        note = usage.get("note")
        prov = usage.get("provenance") or "unknown"

        def _opt_int(key: str) -> int | None:
            v = usage.get(key)
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                return None
            if not math.isfinite(float(v)) or v < 0 or int(v) != v:
                return None
            return int(v)

        total = _opt_int("total_tokens")
        prompt = _opt_int("prompt_tokens")
        completion = _opt_int("completion_tokens")
        if prompt is not None and completion is not None and total != prompt + completion:
            return UsageSettlement(provenance="unknown", note="inconsistent token counts")
        if total is None:
            return UsageSettlement(
                prompt_tokens=prompt,
                completion_tokens=completion,
                total_tokens=None,
                provenance="unknown",
                note=str(note) if note else None,
            )
        return UsageSettlement(
            prompt_tokens=prompt,
            completion_tokens=completion,
            total_tokens=total,
            provenance=str(prov),
            note=str(note) if note else None,
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "calls_started": self.calls_started,
            "tokens_committed": self.tokens_committed,
            "cost_committed": self.cost_committed,
            "outstanding_reservations": len(self.outstanding),
            "max_model_calls": self.max_model_calls,
            "max_tokens": self.max_tokens,
            "max_cost_usd": self.max_cost_usd,
            "settlements": [
                {
                    "total_tokens": s.total_tokens,
                    "provenance": s.provenance,
                    "cost_usd": s.cost_usd,
                    "cost_provenance": s.cost_provenance,
                    "note": s.note,
                }
                for s in self.settlements
            ],
        }
