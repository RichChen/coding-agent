"""Shared structured contracts for tasks, adapter I/O, and run results."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class TaskSpec(BaseModel):
    """Specification for a single repo task benchmark."""

    id: str
    issue: str
    repo_path: str
    test_command: str
    expected_files: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    failure_taxonomy: str | None = None


class RepoInspection(BaseModel):
    """Structured snapshot produced when inspecting a repo for a task."""

    task_id: str
    repo_path: str
    file_count: int
    top_level_entries: list[str]
    test_command: str
    notes: list[str] = Field(default_factory=list)


class CommandResult(BaseModel):
    """Result of running a shell command in the workspace."""

    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: float


class PatchSpec(BaseModel):
    """A file edit to apply in the workspace."""

    path: str
    content: str
    mode: Literal["write", "append"] = "write"


class PatchResult(BaseModel):
    """Outcome of applying a patch."""

    path: str
    applied: bool
    message: str


class TestResult(BaseModel):
    """Structured test execution result."""

    command: str
    passed: bool
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: float


class BaselineMetrics(BaseModel):
    """Metrics collected from a single baseline run."""

    task_id: str
    success: bool
    steps: int
    wall_time_ms: float
    token_estimate: int = 0
    cost_estimate_usd: float = 0.0
    test_passed: bool
    adapter: str
    trace_path: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class BaselineRunResult(BaseModel):
    """Structured output from a single-agent baseline run."""

    task: TaskSpec
    metrics: BaselineMetrics
    diff: str
    inspection: RepoInspection
    test_result: TestResult
    actions: list[dict[str, Any]] = Field(default_factory=list)


class GraphMetrics(BaseModel):
    """Metrics collected from a task-graph execution run."""

    task_id: str
    success: bool
    steps: int
    wall_time_ms: float
    replan_count: int = 0
    test_passed: bool
    adapter: str
    trace_path: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class GraphRunResult(BaseModel):
    """Structured output from a planner + graph execution run."""

    task: TaskSpec
    metrics: GraphMetrics
    diff: str
    inspection: RepoInspection
    test_result: TestResult
    actions: list[dict[str, Any]] = Field(default_factory=list)
