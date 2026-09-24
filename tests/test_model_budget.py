"""HP-03: model budget ledger unit tests."""

from __future__ import annotations

import pytest

from src.policy.model_budget import (
    BudgetLedgerError,
    BudgetRejectReason,
    ModelBudgetLedger,
)


def test_reserve_and_settle_provider_usage():
    ledger = ModelBudgetLedger(max_tokens=1000)
    res = ledger.reserve(estimated_input_tokens=100, max_output_tokens=100)
    assert ledger.tokens_committed == 200
    settlement = ledger.settle(
        res.reservation_id,
        {"prompt_tokens": 80, "completion_tokens": 20, "total_tokens": 100, "provenance": "provider"},
    )
    assert settlement.provenance == "provider"
    assert ledger.tokens_committed == 100


def test_unknown_usage_keeps_reserve():
    ledger = ModelBudgetLedger(max_tokens=500)
    res = ledger.reserve(estimated_input_tokens=50, max_output_tokens=50)
    ledger.settle_unknown(res.reservation_id)
    assert ledger.tokens_committed == 100
    # Next reserve that would exceed must fail.
    with pytest.raises(BudgetLedgerError) as ei:
        ledger.reserve(estimated_input_tokens=250, max_output_tokens=250)
    assert ei.value.reason == BudgetRejectReason.INSUFFICIENT_RESERVE


def test_max_calls():
    ledger = ModelBudgetLedger(max_model_calls=2)
    r1 = ledger.reserve(estimated_input_tokens=1, max_output_tokens=1)
    ledger.settle(r1.reservation_id, {"total_tokens": 1, "provenance": "provider"})
    r2 = ledger.reserve(estimated_input_tokens=1, max_output_tokens=1)
    ledger.settle(r2.reservation_id, {"total_tokens": 1, "provenance": "provider"})
    with pytest.raises(BudgetLedgerError) as ei:
        ledger.reserve(estimated_input_tokens=1, max_output_tokens=1)
    assert ei.value.reason == BudgetRejectReason.MAX_CALLS


def test_cost_requires_price_table():
    ledger = ModelBudgetLedger(max_cost_usd=0.01)
    with pytest.raises(BudgetLedgerError) as ei:
        ledger.reserve(estimated_input_tokens=10, max_output_tokens=10)
    assert ei.value.reason == BudgetRejectReason.NO_PRICE_TABLE


def test_cost_with_price_table():
    ledger = ModelBudgetLedger(
        max_cost_usd=1.0,
        price_table={"prompt_per_1k": 0.1, "completion_per_1k": 0.2},
    )
    res = ledger.reserve(estimated_input_tokens=1000, max_output_tokens=1000)
    assert res.reserved_cost_usd == pytest.approx(0.3)
    ledger.settle(
        res.reservation_id,
        {
            "prompt_tokens": 500,
            "completion_tokens": 500,
            "total_tokens": 1000,
            "provenance": "provider",
        },
    )
    assert ledger.cost_committed == pytest.approx(0.15)


def test_cost_missing_split_keeps_reserve():
    ledger = ModelBudgetLedger(
        max_cost_usd=5.0,
        price_table={"prompt_per_1k": 1.0, "completion_per_1k": 1.0},
    )
    res = ledger.reserve(estimated_input_tokens=100, max_output_tokens=100)
    assert res.reserved_cost_usd == pytest.approx(0.2)
    s = ledger.settle(
        res.reservation_id,
        {"total_tokens": 50, "provenance": "provider"},
    )
    assert s.cost_provenance == "conservative_reserve"
    assert ledger.cost_committed == pytest.approx(0.2)


def test_invalid_price_rejected():
    with pytest.raises(BudgetLedgerError):
        ModelBudgetLedger(
            max_cost_usd=1.0,
            price_table={"prompt_per_1k": float("nan"), "completion_per_1k": 1.0},
        )
