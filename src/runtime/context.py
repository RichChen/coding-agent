"""Context policy wiring for L0/L1 context management.

L0 is enforced by existing ToolContext output limits, configured through
policy.tool_output_max_chars/read_file_max_lines. L1 is the micro-compact hook.
L2 LLM summarisation is intentionally not implemented.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.runtime.compact import MicroCompactHooks
from src.runtime.hooks import LoopHooks


@dataclass(frozen=True)
class ContextPolicyConfig:
    micro_compact: bool = False
    keep_recent_tool_results: int = 3
    compact_token_threshold: int | None = None
    tool_output_max_chars: int | None = None
    read_file_max_lines: int | None = None

    @classmethod
    def from_runtime_config(
        cls,
        runtime_context: dict[str, Any],
        policy_config: dict[str, Any] | None = None,
    ) -> "ContextPolicyConfig":
        policy_config = policy_config or {}
        return cls(
            micro_compact=runtime_context.get("micro_compact", False),
            keep_recent_tool_results=runtime_context.get("keep_recent_tool_results", 3),
            compact_token_threshold=runtime_context.get("compact_token_threshold"),
            tool_output_max_chars=policy_config.get("tool_output_max_chars"),
            read_file_max_lines=policy_config.get("read_file_max_lines"),
        )

    def to_trace_metadata(self) -> dict[str, Any]:
        return {
            "l0_tool_output_max_chars": self.tool_output_max_chars,
            "l0_read_file_max_lines": self.read_file_max_lines,
            "l1_micro_compact": self.micro_compact,
            "l1_keep_recent_tool_results": self.keep_recent_tool_results,
            "l1_compact_token_threshold": self.compact_token_threshold,
            "l2_llm_summary": False,
        }


def build_context_hooks(config: ContextPolicyConfig) -> LoopHooks | None:
    """Build context hooks from config.

    Returns None when no hook is required, preserving baseline behaviour.
    """
    if not config.micro_compact:
        return None
    return MicroCompactHooks(
        keep_recent=config.keep_recent_tool_results,
        token_threshold=config.compact_token_threshold,
    )
