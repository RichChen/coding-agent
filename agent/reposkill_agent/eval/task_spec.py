"""Task catalog loading utilities."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from reposkill_agent.core.contracts import TaskSpec


class TaskCatalog(BaseModel):
    """A collection of benchmark tasks loaded from YAML."""

    tasks: list[TaskSpec] = Field(default_factory=list)

    def get(self, task_id: str) -> TaskSpec | None:
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None


def load_tasks(path: Path, benchmarks_root: Path | None = None) -> TaskCatalog:
    """Load tasks from a YAML file, resolving repo paths relative to benchmarks root."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    root = benchmarks_root or path.parent.parent
    tasks: list[TaskSpec] = []
    for entry in raw.get("tasks", []):
        repo_path = entry["repo_path"]
        if not Path(repo_path).is_absolute():
            repo_path = str((root / repo_path).resolve())
        tasks.append(
            TaskSpec(
                id=entry["id"],
                issue=entry["issue"],
                repo_path=repo_path,
                test_command=entry["test_command"],
                expected_files=entry.get("expected_files", []),
                tags=entry.get("tags", []),
                failure_taxonomy=entry.get("failure_taxonomy"),
            )
        )
    return TaskCatalog(tasks=tasks)
