"""TraceLogger：将每步 StepRecord 以 JSONL 追加写入磁盘。

English: append-only JSONL per run — one line per step + optional run_summary.

每个任务一次 run 对应一个文件：traces/{task_id}_{config}_{timestamp}.jsonl
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from src.tracing.models import StepRecord, TraceRun

logger = logging.getLogger(__name__)


class TraceLogger:
    def __init__(self, output_dir: str = "traces"):
        self.output_dir = Path(output_dir)
        self._file = None
        self._path: Path | None = None

    def open_run(self, task_id: str, config_name: str = "default") -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in task_id)
        self._path = self.output_dir / f"{safe_id}_{config_name}_{ts}.jsonl"
        self._file = open(str(self._path), "w", encoding="utf-8")

    def log_step(self, step: StepRecord) -> None:
        if self._file:
            self._file.write(json.dumps(step.to_dict(), ensure_ascii=False) + "\n")
            self._file.flush()

    def log_run(self, trace: TraceRun) -> None:
        if self._file:
            summary = {
                "type": "run_summary",
                "task_id": trace.task_id,
                "config": trace.config_name,
                "success": trace.success,
                "final_answer": trace.final_answer,
                "failure_reason": trace.failure_reason,
                "total_elapsed_ms": trace.total_elapsed_ms,
                "total_tokens": trace.total_tokens,
                "tool_failures": trace.tool_failures,
                "policy_blocks": trace.policy_blocks,
                "step_count": len(trace.steps),
                "metadata": trace.metadata,
            }
            self._file.write(json.dumps(summary, ensure_ascii=False) + "\n")
            self._file.flush()

    def close(self) -> None:
        if self._file:
            self._file.close()
            self._file = None

    @property
    def path(self) -> Path | None:
        return self._path

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
