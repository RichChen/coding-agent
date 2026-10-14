import pytest

from reposkill_agent.memory.gate import InjectionReceipt, confirm_injection, select_memory
from reposkill_agent.protocol.public import digest
from tests.upgrade_helpers import NOW, facts, policy, task, validated


def choose(records, **kwargs):
    return select_memory(task(), records, facts(), policy(), NOW, decision_id="decision", **kwargs)


def test_valid_selected_not_yet_injected_then_receipt():
    decision = choose([validated()])
    assert decision.items[0].selected
    assert confirm_injection(decision, (), "run") == ()
    c = decision.candidates[0]
    receipt = InjectionReceipt(
        receipt_id="receipt",
        decision_id="decision",
        candidate_id=c.candidate_id,
        requested_hash=c.requested_hash,
        status="injected",
        start_char=0,
        end_char=30,
        actual_hash=digest(c.text[:30]),
        model_operation_id="model-1",
        model_attempt_id="attempt-1",
        reason="host clipped",
    )
    use = confirm_injection(decision, (receipt,), "run")[0]
    assert use.stage == "actually_injected"
    assert use.following == "unknown"
    rejected = receipt.model_copy(update={"status": "rejected", "end_char": 0, "actual_hash": None})
    assert confirm_injection(decision, (rejected,), "run")[0].stage == "rejected"
    with pytest.raises(ValueError, match="unverified_injection"):
        confirm_injection(decision, (receipt.model_copy(update={"actual_hash": "bad"}),), "run")


@pytest.mark.parametrize("status", ["candidate", "stale", "conflicted", "quarantined", "retired"])
def test_lifecycle_blocks_even_high_similarity(status):
    decision = choose([validated(status=status)])
    assert decision.candidates == ()
    assert "status_" + status in decision.items[0].reasons


def test_unknown_conflict_budget_duplicate_and_empty():
    assert choose([]).candidates == ()
    assert not choose([validated()], max_hints=0).candidates
    assert not choose([validated()], max_chars=1).candidates
    assert not choose([validated(dependency_mapping_complete=False)]).candidates
    other_text = "parse_config must instead reject empty config in this repo."
    conflict = validated(
        memory_id="other",
        procedure=other_text,
        content_hash=digest(other_text),
        conflict_group="parser",
    )
    decision = choose([validated(conflict_group="parser"), conflict])
    assert all("unresolved_conflict" in i.reasons for i in decision.items)
    duplicate = validated(memory_id="copy")
    assert len(choose([validated(), duplicate]).candidates) == 1


def test_source_rejection_and_invalid_not_overridden():
    decision = select_memory(task(), [validated()], facts(facts=()), policy(), NOW, decision_id="d")
    assert not decision.candidates
    excluded = policy(allowed_sources=())
    decision = select_memory(task(), [validated()], facts(), excluded, NOW, decision_id="d")
    assert "source_not_allowlisted" in decision.items[0].reasons


def test_unbound_target_cannot_use_source_manifest():
    with pytest.raises(ValueError, match="target_missing"):
        select_memory(
            task(task_id="different"), [validated()], facts(), policy(), NOW, decision_id="d"
        )
