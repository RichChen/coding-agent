"""Episodic memory storage (JSONL + SQLite index)."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class EpisodicMemory(BaseModel):
    """Task-level execution record persisted after each run."""

    task_id: str
    repo_fingerprint: str
    issue_summary: str
    plan_summary: str
    actions: list[dict]
    final_diff_summary: str
    tests: list[dict]
    outcome: Literal["success", "failure"]
    failure_type: str | None = None
    test_output_snippet: str = ""
    expected_files: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EpisodicStore:
    """Append episodic memories to JSONL and index key fields in SQLite."""

    def __init__(self, memory_dir: Path) -> None:
        self.memory_dir = memory_dir
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.jsonl_path = self.memory_dir / "episodic.jsonl"
        self.sqlite_path = self.memory_dir / "memory.db"
        self._init_sqlite()

    def append(self, record: EpisodicMemory) -> None:
        with self.jsonl_path.open("a", encoding="utf-8") as handle:
            handle.write(record.model_dump_json() + "\n")
        with sqlite3.connect(self.sqlite_path) as conn:
            conn.execute(
                """
                INSERT INTO episodic_index
                (task_id, repo_fingerprint, outcome, failure_type, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    record.task_id,
                    record.repo_fingerprint,
                    record.outcome,
                    record.failure_type,
                    record.created_at.isoformat(),
                ),
            )
            conn.commit()

    def list_recent(self, limit: int = 20) -> list[EpisodicMemory]:
        if not self.jsonl_path.exists():
            return []
        lines = self.jsonl_path.read_text(encoding="utf-8").splitlines()
        selected = lines[-limit:]
        return [EpisodicMemory.model_validate_json(line) for line in selected]

    def _init_sqlite(self) -> None:
        with sqlite3.connect(self.sqlite_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS episodic_index (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    repo_fingerprint TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    failure_type TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.commit()
