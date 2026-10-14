"""Transactional knowledge revisions; deliberately not a runtime event store."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from reposkill_agent.memory.records import MemoryRecord, UseRecord
from reposkill_agent.memory.source_manifest import SourcePolicy
from reposkill_agent.protocol.public import canonical, digest

TRANSITIONS = {
    "candidate": {"candidate", "validated", "quarantined", "retired"},
    "validated": {"validated", "stale", "conflicted", "quarantined", "retired"},
    "stale": {"stale", "validated", "quarantined", "retired"},
    "conflicted": {"conflicted", "validated", "quarantined", "retired"},
    "quarantined": {"candidate", "quarantined", "retired"},
    "retired": set(),
}


class RecordStore:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            tables = {
                row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
            if version not in {0, 1} or (version == 0 and tables):
                raise ValueError("unknown_or_legacy_store_schema")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS records (
                    memory_id TEXT, revision INTEGER, payload TEXT NOT NULL,
                    PRIMARY KEY(memory_id, revision));
                CREATE TABLE IF NOT EXISTS transitions (
                    memory_id TEXT, revision INTEGER, reason TEXT, reviewed INTEGER,
                    PRIMARY KEY(memory_id, revision));
                CREATE TABLE IF NOT EXISTS uses (
                    use_id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                PRAGMA user_version=1;
            """)

    def connect(self):
        return sqlite3.connect(self.path)

    def append(
        self,
        record: MemoryRecord,
        *,
        reason: str,
        policy: SourcePolicy | None = None,
        reviewed: bool = False,
    ) -> None:
        # Re-validate even if caller used model_copy/model_construct to bypass Pydantic.
        record = MemoryRecord.model_validate(record.model_dump())
        if not reason:
            raise ValueError("transition_reason_required")
        payload = canonical(record.model_dump(mode="json"))
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute(
                "SELECT payload FROM records WHERE memory_id=? AND revision=?",
                (record.memory_id, record.revision),
            ).fetchone()
            if existing:
                if existing[0] != payload:
                    raise ValueError("revision_collision")
                return
            row = db.execute(
                "SELECT payload FROM records WHERE memory_id=? ORDER BY revision DESC LIMIT 1",
                (record.memory_id,),
            ).fetchone()
            previous = MemoryRecord.model_validate_json(row[0]) if row else None
            if previous is None:
                if record.revision != 1 or record.status not in {"candidate", "quarantined"}:
                    raise ValueError("initial_record_must_be_candidate")
            else:
                if record.revision != previous.revision + 1:
                    raise ValueError("revision_not_sequential")
                if record.status not in TRANSITIONS[previous.status]:
                    raise ValueError("illegal_memory_transition")
                if (
                    previous.status == "quarantined"
                    and record.status == "candidate"
                    and not reviewed
                ):
                    raise ValueError("quarantine_requires_review")
                if record.source_repo_id != previous.source_repo_id or record.kind != previous.kind:
                    raise ValueError("lineage_identity_changed")
                semantic_fields = (
                    "content_hash",
                    "dependencies",
                    "applicability",
                    "sources",
                    "dependency_mapping_complete",
                    "verification_recipe",
                )
                changed = any(getattr(record, k) != getattr(previous, k) for k in semantic_fields)
                if (
                    record.status == "validated"
                    and (changed or previous.status != "validated")
                    and record.validation == previous.validation
                ):
                    raise ValueError("revalidation_required")
            if record.status == "validated":
                if policy is None or policy.reasons(record):
                    raise ValueError("source_policy_rejected")
            db.execute(
                "INSERT INTO records VALUES (?,?,?)", (record.memory_id, record.revision, payload)
            )
            db.execute(
                "INSERT INTO transitions VALUES (?,?,?,?)",
                (record.memory_id, record.revision, reason, int(reviewed)),
            )

    def records(self, *, latest: bool = True) -> list[MemoryRecord]:
        query = (
            "SELECT r.payload FROM records r JOIN "
            "(SELECT memory_id, MAX(revision) v FROM records GROUP BY memory_id) l "
            "ON r.memory_id=l.memory_id AND r.revision=l.v ORDER BY r.memory_id"
            if latest
            else "SELECT payload FROM records ORDER BY memory_id, revision"
        )
        with self.connect() as db:
            return [MemoryRecord.model_validate_json(row[0]) for row in db.execute(query)]

    def record_use(self, use: UseRecord) -> None:
        use = UseRecord.model_validate(use.model_dump())
        payload = canonical(use.model_dump(mode="json"))
        with self.connect() as db:
            if not db.execute(
                "SELECT 1 FROM records WHERE memory_id=? AND revision=?",
                (use.memory_id, use.revision),
            ).fetchone():
                raise ValueError("unknown_memory_revision")
            existing = db.execute(
                "SELECT payload FROM uses WHERE use_id=?", (use.use_id,)
            ).fetchone()
            if existing and existing[0] != payload:
                raise ValueError("use_id_collision")
            db.execute("INSERT OR IGNORE INTO uses VALUES (?,?)", (use.use_id, payload))

    def snapshot(self) -> dict:
        records = [r.model_dump(mode="json") for r in self.records()]
        return {
            "schema_version": "1.0",
            "snapshot_id": digest(canonical(records)),
            "records": records,
        }

    def audit(self) -> dict:
        with self.connect() as db:
            return {
                "transitions": db.execute(
                    "SELECT memory_id,revision,reason,reviewed FROM transitions "
                    "ORDER BY memory_id,revision"
                ).fetchall(),
                "uses": [
                    json.loads(row[0])
                    for row in db.execute("SELECT payload FROM uses ORDER BY use_id")
                ],
            }
