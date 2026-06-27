"""read_events 工具：读取 EventBus 的 JSONL 事件日志（仅 debug 配置启用）。

English: debug-only tool to inspect lifecycle events from an EventBus JSONL file.
Not enabled in hardened config by default.
"""

from __future__ import annotations

from pathlib import Path

from src.tools.base import Tool, ToolContext, ToolResult
from src.tracing.events import EventBus


class ReadEventsTool(Tool):
    """Read the events JSONL file produced by an EventBus.

    This tool is intended for debugging agent lifecycle behaviour.
    It should only be enabled in debug/dev configs, not production.
    """

    name = "read_events"
    description = "Read the lifecycle event log (JSONL) from the current session."
    parameters = {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "Max number of recent events to return. Default: 50.",
            },
        },
    }

    def __init__(self, event_bus: EventBus | None = None):
        self._event_bus = event_bus

    def set_event_bus(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus

    async def execute(self, params: dict, ctx: ToolContext) -> ToolResult:
        limit = params.get("limit", 50)
        call_id = params.get("_call_id", "")

        if self._event_bus is None or self._event_bus.path is None:
            return ToolResult(
                call_id=call_id,
                name=self.name,
                success=False,
                output="",
                error="No event log available for this session.",
            )

        path = self._event_bus.path
        if not path.exists():
            return ToolResult(
                call_id=call_id,
                name=self.name,
                success=False,
                output="",
                error=f"Event log not found: {path}",
            )

        try:
            lines = path.read_text(encoding="utf-8").strip().split("\n")
            recent = lines[-limit:] if len(lines) > limit else lines
            return ToolResult(
                call_id=call_id,
                name=self.name,
                success=True,
                output="\n".join(recent),
            )
        except Exception as e:
            return ToolResult(
                call_id=call_id,
                name=self.name,
                success=False,
                output="",
                error=str(e),
            )
