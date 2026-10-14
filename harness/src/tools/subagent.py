"""Agent-as-Tool: readonly child agent for focused analysis tasks."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from src.llm.client import LLMClient
from src.policy.budget import Budget
from src.policy.sandbox import Sandbox
from src.runtime.loop import AgentLoop
from src.tools.base import SideEffectClass, Tool, ToolContext, ToolResult
from src.tools.files import ListDirTool, ReadFileTool
from src.tools.registry import ToolRegistry
from src.tracing.logger import TraceLogger
from src.tracing.models import TraceRun


READONLY_SUBAGENT_PROMPT = """You are a readonly analysis sub-agent.

You may inspect files and directories, but you must not modify anything.
Return a concise final answer with:
- summary
- files inspected
- findings
- suggested next steps
- confidence
"""


class SubagentTaskTool(Tool):
    """Delegate a focused readonly task to a one-level child AgentLoop."""

    name = "subagent_task"
    description = (
        "Delegate a focused readonly analysis task to a child agent. "
        "The child can only list directories and read files."
    )
    side_effect = SideEffectClass.READ_ONLY
    parameters = {
        "type": "object",
        "properties": {
            "task": {
                "type": "string",
                "description": "Focused readonly analysis task for the child agent.",
            },
        },
        "required": ["task"],
        "additionalProperties": False,
    }

    def __init__(
        self,
        *,
        llm: LLMClient,
        output_dir: str | Path = "traces",
        max_depth: int = 1,
        readonly: bool = True,
        max_steps: int = 3,
        total_timeout_seconds: float = 120.0,
        step_timeout_seconds: float = 60.0,
        file_size_limit_bytes: int | None = None,
        tool_output_max_chars: int | None = None,
        read_file_max_lines: int | None = None,
        model_ledger=None,
    ):
        self.llm = llm
        self.output_dir = Path(output_dir)
        self.max_depth = max_depth
        self.readonly = readonly
        self.max_steps = max_steps
        self.total_timeout_seconds = total_timeout_seconds
        self.step_timeout_seconds = step_timeout_seconds
        self.file_size_limit_bytes = file_size_limit_bytes
        self.tool_output_max_chars = tool_output_max_chars
        self.read_file_max_lines = read_file_max_lines
        self.model_ledger = model_ledger

    async def execute(self, params: dict[str, Any], ctx: ToolContext) -> ToolResult:
        call_id = self.resolve_call_id(params, ctx)
        task = str(params.get("task", "")).strip()

        if not task:
            return ToolResult(
                call_id=call_id,
                name=self.name,
                success=False,
                output="",
                error="Missing required parameter: task",
            )

        if self.max_depth != 1:
            return ToolResult(
                call_id=call_id,
                name=self.name,
                success=False,
                output="",
                error="subagent_task only supports max_depth=1 in this implementation.",
            )

        if not self.readonly:
            return ToolResult(
                call_id=call_id,
                name=self.name,
                success=False,
                output="",
                error="subagent_task is readonly-only in this implementation.",
            )

        child_id = f"subagent_{int(time.time() * 1000)}_{call_id or 'call'}"
        tracer = TraceLogger(output_dir=str(self.output_dir))
        tracer.open_run(child_id, config_name="subagent")

        tools = ToolRegistry()
        tools.register(ReadFileTool())
        tools.register(ListDirTool())

        # Share parent ledger when present; child still has its own step budget but
        # model calls debit the shared ledger. Parent deadline/cancel via cancel_event.
        parent_deadline = ctx.extra.get("deadline")
        parent_cancel = ctx.extra.get("cancel_event")
        child_timeout = self.total_timeout_seconds
        if parent_deadline is not None:
            rem = parent_deadline.remaining()
            if rem is not None:
                child_timeout = min(child_timeout, max(0.01, rem))

        child = AgentLoop(
            llm=self.llm,
            tools=tools,
            sandbox=Sandbox(workspace_root=ctx.workspace_root),
            budget=Budget(
                max_steps=self.max_steps,
                total_timeout_seconds=child_timeout,
                step_timeout_seconds=self.step_timeout_seconds,
                model_ledger=self.model_ledger,
            ),
            tracer=tracer,
            enabled_tools=["read_file", "list_dir"],
            file_size_limit_bytes=self.file_size_limit_bytes,
            tool_output_max_chars=self.tool_output_max_chars,
            read_file_max_lines=self.read_file_max_lines,
            system_prompt=READONLY_SUBAGENT_PROMPT,
            cancel_event=parent_cancel,
            model_ledger=self.model_ledger,
        )
        # Align child run deadline with remaining parent deadline when available.
        if parent_deadline is not None and parent_deadline.run_deadline_mono is not None:
            child.deadline.run_deadline_mono = parent_deadline.run_deadline_mono
            child.deadline.cancel_event = parent_cancel or parent_deadline.cancel_event

        result = await child.run(task, task_id=child_id)
        trace = TraceRun(
            task_id=child_id,
            config_name="subagent",
            steps=result.steps,
            success=result.success,
            final_answer=result.final_answer,
            failure_reason=result.failure_reason.value if result.failure_reason else None,
            total_elapsed_ms=result.total_elapsed_ms,
            total_tokens=result.total_tokens,
            tool_failures=result.tool_failures,
            policy_blocks=result.policy_blocks,
            metadata={"parent_tool_call_id": call_id, "readonly": True, "max_depth": 1},
        )
        tracer.log_run(trace)
        tracer.close()

        trace_path = tracer.path
        if trace_path:
            try:
                trace_file = str(trace_path.relative_to(ctx.workspace_root))
            except ValueError:
                trace_file = str(trace_path)
        else:
            trace_file = ""

        parsed = self._parse_final_answer(result.final_answer or "")
        schema_ok = self._validate_child_schema(parsed)
        payload = {
            "child_task_id": child_id,
            "trace_file": trace_file,
            "summary": parsed["summary"],
            "files_inspected": self._files_inspected(result.steps),
            "findings": parsed["findings"],
            "suggested_next_steps": parsed["suggested_next_steps"],
            "confidence": self._confidence(result.success, result.steps, parsed["confidence"]),
            "success": result.success,
            "failure_reason": result.failure_reason.value,
            "schema_ok": schema_ok,
        }

        event_bus = ctx.extra.get("event_bus")
        if event_bus:
            event_bus.emit(
                "subagent_completed",
                child_task_id=child_id,
                trace_file=payload["trace_file"],
                success=result.success,
            )

        return ToolResult(
            call_id=call_id,
            name=self.name,
            success=result.success,
            output=json.dumps(payload, ensure_ascii=False),
            error=None if result.success else result.failure_reason.value,
        )

    @staticmethod
    def _validate_child_schema(parsed: dict[str, Any]) -> bool:
        summary = str(parsed.get("summary", "")).strip()
        if not summary:
            return False
        if not parsed.get("findings_provided", False):
            return False
        return True

    @staticmethod
    def _files_inspected(steps) -> list[str]:
        files: list[str] = []
        for step in steps:
            for call in step.tool_calls:
                if call.get("name") == "read_file":
                    path = call.get("args", {}).get("path")
                    if path and path not in files:
                        files.append(path)
        return files

    @staticmethod
    def _parse_final_answer(text: str) -> dict[str, Any]:
        summary = text.strip()
        findings: list[str] = []
        next_steps: list[str] = []
        confidence = ""
        current_section = ""

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            normalized = line.lower().rstrip(":")
            if normalized in {"summary", "findings", "suggested next steps", "next steps", "confidence"}:
                current_section = normalized
                continue

            key_match = re.match(r"^(summary|findings|suggested next steps|next steps|confidence)\s*:\s*(.*)$", line, re.I)
            if key_match:
                current_section = key_match.group(1).lower()
                value = key_match.group(2).strip()
                if not value:
                    continue
                if current_section == "summary":
                    summary = value
                elif current_section == "confidence":
                    confidence = value.lower()
                elif current_section in {"findings", "suggested next steps", "next steps"}:
                    target = findings if current_section == "findings" else next_steps
                    target.extend(SubagentTaskTool._split_list_value(value))
                continue

            item = re.sub(r"^[-*]\s*", "", line).strip()
            if current_section == "findings":
                findings.append(item)
            elif current_section in {"suggested next steps", "next steps"}:
                next_steps.append(item)
            elif current_section == "confidence":
                confidence = item.lower()

        findings_provided = bool(findings)
        if not findings and summary:
            findings = [summary]
        return {
            "summary": summary,
            "findings": findings,
            "findings_provided": findings_provided,
            "suggested_next_steps": next_steps,
            "confidence": confidence,
        }

    @staticmethod
    def _split_list_value(value: str) -> list[str]:
        parts = [p.strip(" -") for p in re.split(r";|\n", value) if p.strip(" -")]
        return parts or [value]

    @staticmethod
    def _confidence(success: bool, steps, parsed_confidence: str) -> str:
        if parsed_confidence in {"low", "medium", "high"}:
            return parsed_confidence
        if not success:
            return "low"
        read_count = sum(
            1
            for step in steps
            for call in step.tool_calls
            if call.get("name") == "read_file"
        )
        return "high" if read_count >= 2 else "medium"
