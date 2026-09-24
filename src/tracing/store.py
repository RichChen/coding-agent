"""Single-run SQLite journal. Committed events, never checkpoints, are authoritative.

The writer holds an OS file lock for its entire lifetime; there is no lease or
automatic takeover of a live worker. Use on a local filesystem, not a network share.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path


class StoreError(RuntimeError):
    pass


class RunLocked(StoreError):
    pass


def canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RunLock:
    def __init__(self, path: Path):
        self.file = open(path, "a+b")
        if path.stat().st_size == 0:
            self.file.write(b"0")
            self.file.flush()
        self.file.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self.file.close()
            raise RunLocked("run already has a live writer") from exc

    def close(self):
        self.file.close()  # OS releases the lock, including on process death.


class EventStore:
    SCHEMA = "0.1"
    # Explicit minor extension whitelist; arbitrary envelope fields are rejected.
    OPTIONAL = {"0.1": set(), "0.2": {"diagnostic_code"}}

    def __init__(self, directory: Path, *, create=False, run_id=None, task_id=None,
                 readonly=False, max_event_bytes=16 * 1024 * 1024):
        self.directory = Path(directory).resolve()
        self.readonly = readonly
        self.max_event_bytes = max_event_bytes
        self.lock = None
        self.db = None
        self.started = time.monotonic()
        if create:
            self.directory.mkdir(parents=True, exist_ok=False, mode=0o700)
        if not self.directory.is_dir():
            raise StoreError("run directory missing")
        try:
            if not readonly:
                self.lock = RunLock(self.directory / "writer.lock")
            path = self.directory / "events.sqlite3"
            if not create and not path.is_file():
                raise StoreError("event database missing; refusing to recreate")
            if readonly:
                self.db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
            else:
                self.db = sqlite3.connect(path)
            if self.db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise StoreError("event database integrity check failed")
            if create:
                if readonly or not run_id or not task_id:
                    raise StoreError("new run requires run_id and task_id")
                self.db.executescript('''
                    CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                    CREATE TABLE events (seq INTEGER PRIMARY KEY, event_id TEXT UNIQUE NOT NULL,
                        body TEXT NOT NULL, hash TEXT NOT NULL);
                    CREATE TABLE checkpoint (id INTEGER PRIMARY KEY CHECK(id=1), seq INTEGER, body TEXT);
                ''')
                with self.db:
                    self.db.executemany("INSERT INTO meta VALUES (?,?)", [
                        ("run_id", run_id), ("task_id", task_id), ("schema_version", self.SCHEMA)])
            meta = dict(self.db.execute("SELECT key,value FROM meta"))
            if meta.get("schema_version") != self.SCHEMA:
                raise StoreError("unsupported store schema")
            self.run_id, self.task_id = meta["run_id"], meta["task_id"]
            if not readonly:
                self.db.execute("PRAGMA journal_mode=DELETE")
                self.db.execute("PRAGMA synchronous=FULL")
            events = self.read_events()
            self.seq = len(events)
            self.elapsed_base = events[-1]["elapsed_ms"] if events else 0
            self.used_bytes = sum(len(canonical(e).encode()) for e in events)
        except Exception as exc:
            self.close()
            if isinstance(exc, StoreError):
                raise
            raise StoreError("cannot open valid event database") from exc

    @classmethod
    def validate_event(cls, event):
        required = {"schema_version", "event_id", "run_id", "task_id", "seq", "timestamp",
                    "elapsed_ms", "step_id", "parent_step_id", "operation_id", "attempt_id",
                    "tool_call_id", "event_type", "payload"}
        version = event.get("schema_version")
        if version not in cls.OPTIONAL:
            raise StoreError(f"unsupported event schema: {version}")
        if not required <= event.keys() or event.keys() - required - cls.OPTIONAL[version]:
            raise StoreError("unknown or missing event envelope fields")
        if "diagnostic_code" in event and (not isinstance(event["diagnostic_code"], str) or len(event["diagnostic_code"]) > 128):
            raise StoreError("invalid whitelisted diagnostic extension")
        if type(event["seq"]) is not int or event["seq"] < 1 or not isinstance(event["payload"], dict):
            raise StoreError("invalid event sequence/payload")
        canonical(event)

    def read_events(self):
        events = []
        try:
            for seq, event_id, body, checksum in self.db.execute("SELECT seq,event_id,body,hash FROM events ORDER BY seq"):
                event = json.loads(body)
                self.validate_event(event)
                if (seq != len(events) + 1 or event["seq"] != seq or event["event_id"] != event_id
                        or event["run_id"] != self.run_id or event["task_id"] != self.task_id
                        or digest(body.encode()) != checksum):
                    raise StoreError("event integrity/identity/sequence conflict")
                events.append(event)
        except (sqlite3.DatabaseError, ValueError, TypeError, KeyError) as exc:
            raise StoreError("corrupt event database") from exc
        return events

    def append(self, event_type, payload, *, event_id=None, step_id=None, parent_step_id=None,
               operation_id=None, attempt_id=None, tool_call_id=None):
        if self.readonly or self.db is None:
            raise StoreError("store is not writable")
        event_id = event_id or uuid.uuid4().hex
        content = dict(event_type=event_type, payload=payload, step_id=step_id,
                       parent_step_id=parent_step_id, operation_id=operation_id,
                       attempt_id=attempt_id, tool_call_id=tool_call_id)
        old = self.db.execute("SELECT body FROM events WHERE event_id=?", (event_id,)).fetchone()
        if old:
            event = json.loads(old[0])
            if canonical({k: event[k] for k in content}) != canonical(content):
                raise StoreError("event ID reused with conflicting content")
            return event
        event = dict(schema_version=self.SCHEMA, event_id=event_id, run_id=self.run_id,
                     task_id=self.task_id, seq=self.seq + 1, timestamp=utc_now(),
                     elapsed_ms=self.elapsed_base + (time.monotonic() - self.started) * 1000, **content)
        self.validate_event(event)
        body = canonical(event)
        size = len(body.encode())
        if self.used_bytes + size > self.max_event_bytes:
            raise StoreError("event quota exhausted; no further effects permitted")
        with self.db:
            self.db.execute("INSERT INTO events VALUES (?,?,?,?)",
                            (event["seq"], event_id, body, digest(body.encode())))
        self.seq += 1
        self.used_bytes += size
        return event

    def checkpoint(self, state):
        if self.readonly:
            raise StoreError("read only")
        if len(canonical(state).encode()) > self.max_event_bytes:
            raise StoreError("checkpoint quota exceeded")
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO checkpoint VALUES (1,?,?)", (self.seq, canonical(state)))

    def export_jsonl(self, path: Path):
        # Export is a derivative, never imported as trusted recovery state.
        path = Path(path).resolve()
        if path.suffix != ".jsonl" or path.is_relative_to(self.directory / "artifacts"):
            raise StoreError("export requires a separate .jsonl path")
        from src.tracing.artifacts import atomic_replace
        atomic_replace(path, "".join(canonical(event) + "\n" for event in self.read_events()).encode())

    def close(self):
        if self.db is not None:
            self.db.close()
            self.db = None
        if self.lock is not None:
            self.lock.close()
            self.lock = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def read_jsonl(path: Path):
    lines = Path(path).read_bytes().splitlines()
    events = []
    for index, line in enumerate(lines):
        try:
            event = json.loads(line)
        except (ValueError, UnicodeDecodeError):
            if index == len(lines) - 1:
                return events, "partial_tail; re-export from SQLite"
            raise StoreError("JSONL corruption in middle; refusing partial history")
        EventStore.validate_event(event)
        if event["seq"] != index + 1:
            raise StoreError("JSONL sequence conflict")
        events.append(event)
    return events, "complete"
