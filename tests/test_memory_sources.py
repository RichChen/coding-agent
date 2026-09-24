import json

import pytest

from reposkill_agent.memory.migration import import_legacy
from reposkill_agent.memory.record_store import RecordStore
from reposkill_agent.memory.source_manifest import validate_build_manifest
from tests.upgrade_helpers import NOW, policy, source, validated


@pytest.mark.parametrize(
    "changes",
    [
        {"task_id": "opaque-target"},
        {"split": "heldout"},
        {"protocol_mode": "diagnostic_oracle"},
        {"occurred_at": NOW},
    ],
)
def test_contaminated_manifest_rejected(changes):
    contaminated = policy(allowed_sources=(source(**changes),))
    with pytest.raises(ValueError, match="invalid_source_manifest"):
        validate_build_manifest(contaminated)


def test_same_artifact_under_new_task_name_and_missing_allowlist():
    changed_id = source(task_id="renamed")
    p = policy(
        allowed_sources=(changed_id,), excluded_artifact_hashes=(changed_id.artifact.sha256,)
    )
    with pytest.raises(ValueError, match="heldout_artifact"):
        validate_build_manifest(p)
    assert "source_not_allowlisted" in policy(allowed_sources=()).reasons(validated())


def test_legacy_copy_import_excludes_oracle_and_secret(tmp_path):
    src = tmp_path / "legacy.jsonl"
    lines = [
        {"pattern": "parse config publicly"},
        {"pattern": "ORACLE_SENTINEL", "expected_files": ["answer.py"]},
        {"pattern": "api_key=FAKE_ONLY_123456"},
    ]
    src.write_text("\n".join(json.dumps(v) for v in lines) + "\n{bad", encoding="utf-8")
    before = src.read_bytes()
    store = RecordStore(tmp_path / "new.db")
    result = import_legacy(src, store)
    assert src.read_bytes() == before
    assert [row["status"] for row in result] == [
        "candidate",
        "quarantined",
        "quarantined",
        "quarantined",
    ]
    assert store.records()[0].sources == ()
    assert "ORACLE_SENTINEL" not in json.dumps(store.snapshot())
    assert "FAKE_ONLY" not in json.dumps(result)
