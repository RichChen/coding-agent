"""Procedural memory storage."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field


class ProceduralMemory(BaseModel):
    """Reusable workflow abstracted from successful tasks."""

    id: str
    source_task_ids: list[str]
    pattern: str
    reusable_workflow: list[str]
    applies_when: list[str]
    verifier: str
    confidence: float
    likely_files: list[str] = Field(default_factory=list)
    repo_convention: str = ""
    diff_hint: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ProceduralStore:
    """JSONL store for procedural memory records."""

    def __init__(self, memory_dir: Path) -> None:
        self.memory_dir = memory_dir
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.jsonl_path = self.memory_dir / "procedural.jsonl"

    def append(self, record: ProceduralMemory) -> None:
        with self.jsonl_path.open("a", encoding="utf-8") as handle:
            handle.write(record.model_dump_json() + "\n")

    def list_all(self) -> list[ProceduralMemory]:
        if not self.jsonl_path.exists():
            return []
        lines = self.jsonl_path.read_text(encoding="utf-8").splitlines()
        return [ProceduralMemory.model_validate_json(line) for line in lines]
