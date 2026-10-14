import json
import sqlite3
from pathlib import Path

import pytest

from src.tracing.artifacts import ArtifactStore
from src.tracing.store import EventStore, RunLocked, StoreError, canonical, read_jsonl


def test_commits_ids_conflicts_and_readonly_replay(tmp_path):
    run = tmp_path / "run"
    with EventStore(run, create=True, run_id="r", task_id="t") as store:
        first = store.append("fixture", {"n": 1}, event_id="fixed")
        assert store.append("fixture", {"n": 1}, event_id="fixed") == first
        with pytest.raises(StoreError, match="conflicting"):
            store.append("fixture", {"n": 2}, event_id="fixed")
        with pytest.raises(RunLocked):
            EventStore(run)
        with EventStore(run, readonly=True) as reader:
            assert reader.read_events() == [first]
            with pytest.raises(StoreError):
                reader.append("oops", {})
        store.checkpoint({"deliberately": "stale"})
        with pytest.raises(StoreError, match="export"):
            store.export_jsonl(run / "events.sqlite3")
    with EventStore(run) as reopened:
        assert reopened.append("fixture", {})["seq"] == 2


def test_database_corruption_and_missing_fail_closed(tmp_path):
    run = tmp_path / "run"
    with EventStore(run, create=True, run_id="r", task_id="t"):
        pass
    (run / "events.sqlite3").write_bytes(b"not sqlite")
    with pytest.raises(StoreError):
        EventStore(run)
    assert (run / "events.sqlite3").read_bytes() == b"not sqlite"
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(StoreError, match="missing"):
        EventStore(empty)
    assert not (empty / "events.sqlite3").exists()


def test_jsonl_tail_middle_and_schema_whitelist(tmp_path):
    path = tmp_path / "events.jsonl"
    with EventStore(tmp_path / "run", create=True, run_id="r", task_id="t") as store:
        first = store.append("fixture", {})
        store.append("fixture", {})
        store.export_jsonl(path)
    assert read_jsonl(path)[1] == "complete"
    data = path.read_bytes()
    path.write_bytes(data + b'{"seq":')
    events, status = read_jsonl(path)
    assert len(events) == 2 and status.startswith("partial_tail")
    path.write_bytes(data.splitlines()[0] + b"\nBAD\n" + data.splitlines()[1])
    with pytest.raises(StoreError, match="middle"):
        read_jsonl(path)
    EventStore.validate_event(dict(first, schema_version="0.2", diagnostic_code="x"))
    for changed in [dict(first, schema_version="1.0"), dict(first, oracle={"gold": "x"})]:
        with pytest.raises(StoreError):
            EventStore.validate_event(changed)
    with pytest.raises(StoreError, match="extension"):
        EventStore.validate_event(dict(first, schema_version="0.2", diagnostic_code={"gold_patch": "secret"}))


def test_artifact_integrity_ownership_and_orphan_quota(tmp_path):
    artifacts = ArtifactStore(tmp_path / "artifacts", "run-a", limit_bytes=8, item_limit_bytes=8)
    ref = artifacts.publish(b"1234")
    assert artifacts.read(ref) == b"1234"
    assert artifacts.publish(b"1234") == ref
    with pytest.raises(StoreError, match="ownership"):
        artifacts.read(dict(ref, run_id="run-b"))
    # Unreferenced objects still consume quota.
    artifacts.publish(b"5678")
    with pytest.raises(StoreError, match="quota"):
        artifacts.publish(b"9")
    (artifacts.root / ref["path"]).write_bytes(b"xxxx")
    with pytest.raises(StoreError, match="hash"):
        artifacts.read(ref)


def test_event_quota_cannot_start_another_intent(tmp_path):
    with EventStore(tmp_path / "run", create=True, run_id="r", task_id="t", max_event_bytes=1024) as store:
        store.append("tool.intent", {})
        with pytest.raises(StoreError, match="quota"):
            store.append("tool.intent", {"large": "x" * 1024})
        assert len(store.read_events()) == 1
