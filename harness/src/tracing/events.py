"""Lifecycle EventBus：在 agent 生命周期关键点发射 JSONL 事件。

English: structured event emitter — appends one JSON object per line
to {output_dir}/events.jsonl. Used for debugging and observability,
not for critical-path logic.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class EventBus:
    """Append-only JSONL event log.

    NOT a pub/sub bus — just structured logging for lifecycle events.
    """

    def __init__(self, output_dir: str | Path = "traces"):
        self.output_dir = Path(output_dir)
        self._file = None
        self._path: Path | None = None

    def open(self, task_id: str) -> None:
        if self._file is not None:
            return  # already open
        self.output_dir.mkdir(parents=True, exist_ok=True)
        ts = int(time.time() * 1000)
        safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in task_id)
        self._path = self.output_dir / f"events_{safe_id}_{ts}.jsonl"
        self._file = open(str(self._path), "w", encoding="utf-8")

    def emit(self, event: str, **payload: Any) -> None:
        if not self._file:
            return
        record = {
            "event": event,
            "timestamp_epoch_ms": int(time.time() * 1000),
            **payload,
        }
        self._file.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._file.flush()

    def close(self) -> None:
        if self._file:
            self._file.close()
            self._file = None

    @property
    def path(self) -> Path | None:
        return self._path
