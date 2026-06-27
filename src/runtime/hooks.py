"""Loop 前置/后置 Hook 管线。

English: pluggable hooks that run before LLM calls and after tool execution.
Default no-op: when hooks is None, behaviour is identical to before.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class HookContext:
    """Context passed to hooks — mutable snapshot of current loop state."""

    step_number: int = 0
    workspace_root: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


class LoopHooks:
    """Pluggable hook interface for the agent loop.

    Subclass and override. Return modified messages (or the same list).
    """

    async def before_llm(self, messages: list[dict], ctx: HookContext) -> list[dict]:
        """Called right before each LLM call. Receives current messages list."""
        return messages

    async def after_tools(self, messages: list[dict], ctx: HookContext) -> list[dict]:
        """Called after all tool results have been appended to messages."""
        return messages
