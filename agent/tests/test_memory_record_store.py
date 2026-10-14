import sqlite3

import pytest

from reposkill_agent.memory.record_store import RecordStore
from reposkill_agent.memory.records import MemoryRecord
from tests.upgrade_helpers import policy, record, validated


def test_atomic_revisions_and_immutability(tmp_path):
    store = RecordStore(tmp_path / "records.db")
    initial = record()
    store.append(initial, reason="build")
    store.append(initial, reason="same")
    store.append(validated(), reason="public tests", policy=policy())
    assert len(store.records(latest=False)) == 2
    assert len(store.audit()["transitions"]) == 2
    with pytest.raises(ValueError, match="revision_collision"):
        store.append(validated(conflict_group="different"), reason="overwrite", policy=policy())
    assert store.snapshot() == store.snapshot()


def test_transaction_failure_rolls_back_record(tmp_path):
    store = RecordStore(tmp_path / "records.db")
    with store.connect() as db:
        db.execute(
            "CREATE TRIGGER fail_transition BEFORE INSERT ON transitions "
            "BEGIN SELECT RAISE(ABORT, 'fault injection'); END"
        )
    with pytest.raises(sqlite3.IntegrityError, match="fault injection"):
        store.append(record(), reason="build")
    assert store.records() == []


def test_transition_validation_and_quarantine_review(tmp_path):
    store = RecordStore(tmp_path / "records.db")
    with pytest.raises(ValueError, match="initial_record"):
        store.append(validated(), reason="skip candidate", policy=policy())
    store.append(record(status="quarantined"), reason="source failure")
    data = record().model_dump()
    data.update(revision=2, supersedes=1)
    with pytest.raises(ValueError, match="quarantine_requires_review"):
        store.append(MemoryRecord(**data), reason="automatic recovery")
    store.append(MemoryRecord(**data), reason="reviewed source", reviewed=True)
    assert store.records()[0].status == "candidate"


def test_no_default_profile_and_no_policy_promotion(tmp_path):
    store = RecordStore(tmp_path / "records.db")
    assert store.records() == []
    store.append(record(), reason="build")
    with pytest.raises(ValueError, match="source_policy"):
        store.append(validated(), reason="trust me")
    assert store.records()[0].status == "candidate"
