"""JSONL trace utilities for run observability."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field


class TraceEvent(BaseModel):
    """A single structured trace event written to JSONL."""

    run_id: str
    task_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    event_type: Literal[
        "run_start",
        "run_end",
        "inspect",
        "action",
        "command",
        "patch",
        "test",
        "diff",
        "metric",
        "error",
        "plan_created",
        "node_start",
        "node_end",
        "replan",
    ]
    agent_role: str = "single_agent"
    payload: dict[str, Any] = Field(default_factory=dict)


class TraceWriter:
    """Append-only JSONL trace writer."""

    def __init__(self, path: Path, run_id: str, task_id: str) -> None:
        self.path = path
        self.run_id = run_id
        self.task_id = task_id
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def emit(
        self,
        event_type: str,
        payload: dict[str, Any] | None = None,
        agent_role: str = "single_agent",
    ) -> TraceEvent:
        """Write one trace event and return it."""
        event = TraceEvent(
            run_id=self.run_id,
            task_id=self.task_id,
            event_type=event_type,
            agent_role=agent_role,
            payload=payload or {},
        )
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(event.model_dump_json() + "\n")
        return event
