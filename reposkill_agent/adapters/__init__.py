"""Workspace adapters for repo task execution."""

from reposkill_agent.adapters.base import WorkspaceAdapter
from reposkill_agent.adapters.fake_adapter import FakeAdapter

__all__ = ["FakeAdapter", "WorkspaceAdapter"]
