"""Abstract workspace adapter interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from reposkill_agent.core.contracts import (
    CommandResult,
    PatchResult,
    PatchSpec,
    RepoInspection,
    TaskSpec,
    TestResult,
)


class WorkspaceAdapter(ABC):
    """Unified interface for repo workspace operations.

    Upper layers must depend only on this interface, never on OpenHands SDK directly.
    """

    @abstractmethod
    def inspect_repo(self, task: TaskSpec) -> RepoInspection:
        """Inspect the repo associated with a task."""

    @abstractmethod
    def run_command(self, command: str) -> CommandResult:
        """Run a shell command in the workspace."""

    @abstractmethod
    def apply_patch(self, patch: PatchSpec) -> PatchResult:
        """Apply a file patch in the workspace."""

    @abstractmethod
    def read_file(self, path: str) -> str:
        """Read a file from the workspace."""

    @abstractmethod
    def list_files(self, pattern: str = "**/*") -> list[str]:
        """List files matching a glob pattern relative to the workspace."""

    @abstractmethod
    def run_tests(self, test_command: str) -> TestResult:
        """Run the project test command."""

    @abstractmethod
    def produce_diff(self) -> str:
        """Return a unified diff of workspace changes since adapter init."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Adapter identifier for traces and metrics."""
