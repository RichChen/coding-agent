"""Baseline runner contracts for external and vanilla comparisons."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Protocol

from pydantic import BaseModel, Field

BaselineStatus = Literal["success", "failure", "skipped", "error"]


class BaselineRunRequest(BaseModel):
    """Input for a single baseline run on one benchmark task."""

    task_id: str
    issue: str
    repo_path: Path
    test_command: str
    expected_files: list[str] = Field(default_factory=list)
    output_dir: Path


class BaselineRunResult(BaseModel):
    """Outcome of one baseline run."""

    name: str
    task_id: str
    status: BaselineStatus
    skip_reason: str = ""
    test_passed: bool = False
    wall_time_ms: float = 0.0
    llm_calls: int = 0
    diff_summary: str = ""
    report_path: str = ""
    stdout_preview: str = ""
    stderr_preview: str = ""


class BaselineRunner(Protocol):
    """Protocol implemented by each baseline adapter."""

    name: str

    def is_available(self) -> tuple[bool, str]:
        """Return (available, skip_reason_if_not)."""
        ...

    def run(self, request: BaselineRunRequest) -> BaselineRunResult:
        ...
