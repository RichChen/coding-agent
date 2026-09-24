import pytest
from pydantic import ValidationError

from reposkill_agent.memory.records import BuildUsage, MemoryRecord, UseRecord
from tests.upgrade_helpers import record, validated


def test_roundtrip_and_missing_provenance():
    r = validated()
    assert MemoryRecord.model_validate_json(r.model_dump_json()) == r
    assert r.hint()["sources"][0]["task_id"] == "past-task"
    with pytest.raises(ValidationError, match="missing_public_validation"):
        validated(sources=())
    assert record(sources=()).status == "candidate"


def test_secrets_and_unknown_schema_rejected():
    with pytest.raises(ValidationError, match="secret_content"):
        from reposkill_agent.protocol.public import digest

        record(
            procedure="api_key=FAKE_TEST_ONLY_123",
            content_hash=digest("api_key=FAKE_TEST_ONLY_123"),
        )
    with pytest.raises(ValidationError, match="unsupported_schema_major"):
        record(schema_version="2.0")
    with pytest.raises(ValidationError, match="memory_content_hash"):
        record(content_hash="0" * 64)


def test_unknown_usage_and_use_stage_evidence():
    usage = BuildUsage(method="llm", model="fixture-model", calls=1, token_status="unknown")
    assert usage.cost is None
    with pytest.raises(ValidationError):
        BuildUsage(method="llm")
    with pytest.raises(ValidationError, match="injection_requires"):
        UseRecord(
            use_id="u",
            run_id="r",
            decision_id="d",
            memory_id="m",
            revision=1,
            stage="actually_injected",
            reason="selected",
        )
