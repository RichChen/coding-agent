import pytest

from src.eval.contracts import ContractError, PublicTask


def test_public_task_rejects_nested_oracle_fields():
    for value in [
        {"id": "x", "description": "do", "gold": "secret"},
        {"id": "x", "description": "do", "public_context": {"nested": {"hidden_tests": []}}},
        {"id": "x", "description": "do", "context": {"oracle": "secret"}},
    ]:
        with pytest.raises(ContractError):
            PublicTask.from_mapping(value)


def test_public_task_agent_payload_contains_only_public_fields():
    task = PublicTask.from_mapping({"id": "x", "description": "fix", "budget": {"max": 1}})
    assert task.agent_payload()["description"] == "fix"
    assert "gold" not in repr(task.agent_payload())


def test_unknown_public_fields_rejected():
    with pytest.raises(ContractError, match="forbidden|unknown"):
        PublicTask.from_mapping({"id": "x", "description": "fix", "expected": {}})
