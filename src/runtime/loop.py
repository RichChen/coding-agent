"""AgentLoop：plan → act → observe 主循环（Coding Harness 的核心）。

English: core agent loop — system prompt + tools, LLM round-trip, tool execution,
budget/tracing hooks, terminal conditions.

单次任务流程概览：
  1. 拼装 system prompt 与 tools schema，发送用户任务到 LLM。
  2. 若返回纯文本且无 tool_calls → 视为最终答案并结束。
  3. 若有 tool_calls → 经策略与沙箱执行工具，将 tool 消息写回 messages，再循环。
  4. 终止条件：最终答案、步数上限、总超时/单步超时、或不可恢复的 LLM 错误。
"""

from __future__ import annotations

import asyncio
import enum
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

from src.llm.client import LLMClient, LLMError, LLMErrorKind, LLMResponse, ToolCall
from src.policy.budget import Budget, BudgetExhausted
from src.policy.sandbox import Sandbox
from src.runtime.hooks import HookContext, LoopHooks
from src.runtime.planner import Plan, SimplePlanner
from src.runtime.retry import RetryConfig, RetryPolicy
from src.runtime.state import AgentState, LoopPhase
from src.tools.base import ToolContext, ToolResult
from src.tools.registry import ToolRegistry
from src.tracing.events import EventBus
from src.tracing.logger import TraceLogger
from src.tracing.models import StepRecord, TraceRun

logger = logging.getLogger(__name__)

# 以下 system prompt 故意使用英文：便于多数 LLM 遵循工具与格式约定；勿改为中文除非你有对照实验需求。
SYSTEM_PROMPT = """You are a coding agent. Your job is to complete tasks by reasoning and using tools.

Workflow:
1. Think about what the task requires.
2. Use tools to read files, explore the workspace, and make changes.
3. When the task is complete, respond with a final answer explaining what you did.

Rules:
- All file paths are relative to the workspace root. Do not use absolute paths.
- Write complete, working code. Do not use placeholders.
- If a tool returns an error, read the error and try a different approach.
- When you are done, do NOT call any more tools. Just provide your final answer."""


class FailureReason(str, enum.Enum):
    NONE = "none"
    TIMEOUT = "timeout"
    TOOL_ERROR = "tool_error"
    POLICY_BLOCK = "policy_block"
    MODEL_PARSE_ERROR = "model_parse_error"
    STEP_LIMIT = "step_limit"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


@dataclass
class AgentRunResult:
    task_id: str
    success: bool
    final_answer: str | None = None
    failure_reason: FailureReason = FailureReason.NONE
    steps: list[StepRecord] = field(default_factory=list)
    total_elapsed_ms: float = 0.0
    total_tokens: int = 0
    tool_failures: int = 0
    policy_blocks: int = 0
    total_tool_invocations: int = 0
    plan: dict | None = None
    context_events: list[dict] = field(default_factory=list)
    subagent_traces: list[dict] = field(default_factory=list)


class AgentLoop:
    """主循环：维护对话 messages 与每轮工具执行（conversation + tool cycle）。"""

    def __init__(
        self,
        llm: LLMClient,
        tools: ToolRegistry,
        sandbox: Sandbox,
        budget: Budget,
        retry_config: RetryConfig | None = None,
        tracer: TraceLogger | None = None,
        enabled_tools: list[str] | None = None,
        file_size_limit_bytes: int | None = None,
        tool_output_max_chars: int | None = None,
        read_file_max_lines: int | None = None,
        hooks: LoopHooks | None = None,
        event_bus: EventBus | None = None,
        system_prompt: str | None = None,
        runtime_mode: str = "react",
        planner: SimplePlanner | None = None,
        use_llm_stream: bool = False,
        cancel_event: asyncio.Event | None = None,
    ):
        self.llm = llm
        self.tools = tools
        self.sandbox = sandbox
        self.budget = budget
        self.retry = RetryPolicy(retry_config or RetryConfig())
        self.tracer = tracer
        self.enabled_tools = enabled_tools
        self.file_size_limit_bytes = file_size_limit_bytes
        self.tool_output_max_chars = tool_output_max_chars
        self.read_file_max_lines = read_file_max_lines
        self.hooks = hooks
        self.event_bus = event_bus
        self.system_prompt = system_prompt if system_prompt else SYSTEM_PROMPT
        self.runtime_mode = runtime_mode
        self.planner = planner
        self.use_llm_stream = use_llm_stream
        self.cancel_event = cancel_event

    def _check_cancelled(self, task_id: str) -> AgentRunResult | None:
        if self.cancel_event and self.cancel_event.is_set():
            if self.event_bus:
                self.event_bus.emit("run_end", success=False, reason="cancelled")
            return AgentRunResult(
                task_id=task_id,
                success=False,
                failure_reason=FailureReason.CANCELLED,
            )
        return None

    async def _call_llm(
        self,
        messages: list[dict],
        tool_schemas: list[dict],
        step_number: int,
    ) -> LLMResponse:
        """Invoke LLM via chat() or stream_chat(), optionally emitting stream events."""
        if not self.use_llm_stream:
            return await self.retry.execute(self.llm.chat, messages, tool_schemas)

        async def _stream_collect() -> LLMResponse:
            text: str | None = None
            tool_calls: list[ToolCall] = []
            finish_reason = "stop"
            usage: dict[str, int] = {}
            async for event in self.llm.stream_chat(messages, tool_schemas):
                if self.event_bus:
                    self.event_bus.emit(event.event, step=step_number, **event.data)
                if event.event == "message_delta":
                    text = event.data.get("text")
                elif event.event == "tool_call_delta":
                    tool_calls.append(
                        ToolCall(
                            id=event.data["id"],
                            name=event.data["name"],
                            arguments=event.data.get("arguments", {}),
                        )
                    )
                elif event.event == "llm_stream_done":
                    finish_reason = event.data.get("finish_reason", "stop")
                    usage = event.data.get("usage", {})
                elif event.event == "llm_error":
                    kind = LLMErrorKind(event.data.get("kind", LLMErrorKind.UNKNOWN.value))
                    raise LLMError(event.data.get("message", "LLM error"), kind=kind)
            return LLMResponse(
                text=text,
                tool_calls=tool_calls,
                finish_reason=finish_reason,
                usage=usage,
            )

        return await self.retry.execute(_stream_collect)

    async def run(self, task_description: str, task_id: str = "unknown") -> AgentRunResult:
        """对单条任务执行完整 agent 循环。

        Args:
            task_description: 自然语言任务描述。
            task_id: 用于 trace / 评测报表的任务标识。

        Returns:
            AgentRunResult：含每步记录与汇总统计。
        """
        workspace_root = self.sandbox.workspace_root
        state = AgentState()
        steps: list[StepRecord] = []
        total_tokens = 0
        tool_failures = 0
        policy_blocks = 0
        total_tool_invocations = 0
        start_time = time.monotonic()
        plan: Plan | None = None
        replan_used = False
        context_events: list[dict] = []
        subagent_traces: list[dict] = []

        # 初始 messages：system + user（tools schema 每轮相同，由 LLMClient 附带）
        tool_schemas = self.tools.schemas(self.enabled_tools)
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": task_description},
        ]

        if self.runtime_mode == "plan_act" and self.planner:
            plan = self.planner.create_plan(task_description, self.enabled_tools)
            messages.append(
                {
                    "role": "system",
                    "content": (
                        "Current execution plan. Use it to guide tool choices; "
                        "do not treat it as user-visible output.\n"
                        f"{plan.to_prompt_text()}"
                    ),
                }
            )

        self.budget.start()

        if self.event_bus:
            self.event_bus.open(task_id)
            self.event_bus.emit("run_start", task_id=task_id)
            if plan:
                self.event_bus.emit("plan_created", task_id=task_id, plan=plan.to_dict())

        try:
            while True:
                cancelled = self._check_cancelled(task_id)
                if cancelled:
                    return cancelled

                self.budget.check_step_timeout()

                # ---- THINKING：等待 LLM ----
                state.transition(LoopPhase.THINKING)
                self.budget.start_step()

                # Hook: before LLM call (e.g. micro-compact)
                if self.hooks:
                    hook_ctx = HookContext(
                        step_number=state.step_number,
                        workspace_root=str(workspace_root),
                    )
                    messages = await self.hooks.before_llm(messages, hook_ctx)
                    context_stats = hook_ctx.extra.get("context_stats")
                    if context_stats and context_stats.get("did_compact"):
                        context_event = {
                            "step": state.step_number,
                            **context_stats,
                        }
                        context_events.append(context_event)
                        if self.event_bus:
                            self.event_bus.emit(
                                "context_compacted",
                                task_id=task_id,
                                **context_event,
                            )

                step_start = time.monotonic()
                try:
                    response: LLMResponse = await self._call_llm(
                        messages, tool_schemas, state.step_number
                    )
                except Exception as e:
                    logger.error(f"LLM call failed: {e}")
                    state.record_failure(str(e))
                    steps.append(
                        StepRecord(
                            step=state.step_number,
                            phase=LoopPhase.FAILED,
                            messages_snapshot=len(messages),
                            llm_text=None,
                            tool_calls=[],
                            tool_results=[],
                            elapsed_ms=(time.monotonic() - step_start) * 1000,
                        )
                    )
                    if self.event_bus:
                        self.event_bus.emit("run_end", success=False, reason="model_parse_error")
                    return AgentRunResult(
                        task_id=task_id,
                        success=False,
                        failure_reason=FailureReason.MODEL_PARSE_ERROR,
                        steps=steps,
                        total_elapsed_ms=(time.monotonic() - start_time) * 1000,
                        total_tokens=total_tokens,
                        tool_failures=tool_failures,
                        policy_blocks=policy_blocks,
                        total_tool_invocations=total_tool_invocations,
                        plan=plan.to_dict() if plan else None,
                        context_events=context_events,
                        subagent_traces=subagent_traces,
                    )

                total_tokens += response.usage.get("total_tokens", 0)
                step_elapsed = (time.monotonic() - step_start) * 1000

                if self.event_bus:
                    self.event_bus.emit(
                        "llm_complete",
                        step=state.step_number,
                        has_tool_calls=response.has_tool_calls,
                        tool_count=len(response.tool_calls),
                        elapsed_ms=round(step_elapsed, 2),
                        model=getattr(self.llm, "model", None),
                        usage=response.usage,
                    )

                # ---- 无 tool_calls：视为最终自然语言答案 ----
                if not response.has_tool_calls:
                    state.transition(LoopPhase.DONE)
                    if plan:
                        plan.mark_done()
                    steps.append(
                        StepRecord(
                            step=state.step_number,
                            phase=LoopPhase.DONE,
                            messages_snapshot=len(messages),
                            llm_text=response.text,
                            tool_calls=[],
                            tool_results=[],
                            elapsed_ms=step_elapsed,
                        )
                    )
                    if self.event_bus:
                        self.event_bus.emit("run_end", success=True)
                    return AgentRunResult(
                        task_id=task_id,
                        success=True,
                        final_answer=response.text,
                        steps=steps,
                        total_elapsed_ms=(time.monotonic() - start_time) * 1000,
                        total_tokens=total_tokens,
                        tool_failures=tool_failures,
                        policy_blocks=policy_blocks,
                        total_tool_invocations=total_tool_invocations,
                        plan=plan.to_dict() if plan else None,
                        context_events=context_events,
                        subagent_traces=subagent_traces,
                    )

                # ---- ACTING：执行本轮所有 tool_calls ----
                state.transition(LoopPhase.ACTING)

                cancelled = self._check_cancelled(task_id)
                if cancelled:
                    return cancelled

                # OpenAI 格式：assistant 消息携带 tool_calls，后续每条 tool 结果单独一条 message
                assistant_msg = {
                    "role": "assistant",
                    "content": response.text,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": self._serialize_args(tc.arguments),
                            },
                        }
                        for tc in response.tool_calls
                    ],
                }
                messages.append(assistant_msg)

                # 顺序执行每个 tool_call（同一轮内串行）
                tool_results: list[ToolResult] = []
                for tc in response.tool_calls:
                    total_tool_invocations += 1
                    tool = self.tools.get(tc.name)
                    if tool is None:
                        tr = ToolResult(
                            call_id=tc.id,
                            name=tc.name,
                            success=False,
                            output="",
                            error=f"Unknown tool: {tc.name}",
                        )
                        tool_failures += 1
                    else:
                        tc.arguments["_call_id"] = tc.id
                        ctx = ToolContext(
                            workspace_root=workspace_root,
                            sandbox=self.sandbox,
                            file_size_limit_bytes=self.file_size_limit_bytes,
                            tool_output_max_chars=self.tool_output_max_chars,
                            read_file_max_lines=self.read_file_max_lines,
                            extra={"event_bus": self.event_bus} if self.event_bus else {},
                        )
                        tr = await tool.execute(tc.arguments, ctx)
                        if not tr.success:
                            tool_failures += 1
                            if tr.error and "policy" in tr.error.lower():
                                policy_blocks += 1

                    tool_results.append(tr)
                    messages.append(tr.to_message())
                    if tc.name == "subagent_task" and tr.success:
                        subagent_trace = self._extract_subagent_trace(tr.output)
                        if subagent_trace:
                            subagent_traces.append(subagent_trace)

                # Hook: after all tool results appended (e.g. compaction)
                if self.hooks:
                    hook_ctx = HookContext(
                        step_number=state.step_number,
                        workspace_root=str(workspace_root),
                    )
                    messages = await self.hooks.after_tools(messages, hook_ctx)

                if self.event_bus and response.has_tool_calls:
                    self.event_bus.emit(
                        "tools_complete",
                        step=state.step_number,
                        success_count=sum(1 for r in tool_results if r.success),
                        failure_count=sum(1 for r in tool_results if not r.success),
                    )

                # ---- OBSERVING：记录本步 trace，准备进入下一轮 THINKING ----
                state.transition(LoopPhase.OBSERVING)
                if plan:
                    plan_changed = False
                    if (
                        not replan_used
                        and any(not r.success for r in tool_results)
                        and plan.maybe_replan("tool failure")
                    ):
                        replan_used = True
                        plan_changed = True
                        if self.event_bus:
                            self.event_bus.emit(
                                "plan_replanned",
                                step=state.step_number,
                                reason="tool_failure",
                                plan=plan.to_dict(),
                            )
                    else:
                        if plan.advance_after_tools(
                            [tc.name for tc in response.tool_calls],
                            success_count=sum(1 for r in tool_results if r.success),
                        ):
                            plan_changed = True
                    if self.event_bus:
                        self.event_bus.emit(
                            "plan_updated",
                            step=state.step_number,
                            plan=plan.to_dict(),
                        )
                    if plan_changed:
                        messages.append(
                            {
                                "role": "system",
                                "content": "Plan update: " + plan.to_prompt_text(),
                            }
                        )

                steps.append(
                    StepRecord(
                        step=state.step_number,
                        phase=LoopPhase.ACTING,
                        messages_snapshot=len(messages),
                        llm_text=response.text,
                        tool_calls=[
                            {"name": tc.name, "args": tc.arguments}
                            for tc in response.tool_calls
                        ],
                        tool_results=[
                            {"name": r.name, "success": r.success, "output": r.output[:500]}
                            for r in tool_results
                        ],
                        elapsed_ms=step_elapsed,
                    )
                )

                if self.tracer:
                    self.tracer.log_step(steps[-1])

                state.step_number += 1

        except BudgetExhausted as e:
            logger.warning(f"Budget exhausted: {e.reason}")
            is_timeout = "timeout" in e.reason.lower()
            if self.event_bus:
                self.event_bus.emit("budget_exhausted", reason=e.reason)
                self.event_bus.emit("run_end", success=False, reason=e.reason)
            return AgentRunResult(
                task_id=task_id,
                success=False,
                failure_reason=FailureReason.TIMEOUT if is_timeout else FailureReason.STEP_LIMIT,
                steps=steps,
                total_elapsed_ms=(time.monotonic() - start_time) * 1000,
                total_tokens=total_tokens,
                tool_failures=tool_failures,
                policy_blocks=policy_blocks,
                total_tool_invocations=total_tool_invocations,
                plan=plan.to_dict() if plan else None,
                context_events=context_events,
                subagent_traces=subagent_traces,
            )
        finally:
            if self.event_bus:
                self.event_bus.close()

    @staticmethod
    def _serialize_args(args: dict) -> str:
        return json.dumps(args, ensure_ascii=False)

    @staticmethod
    def _extract_subagent_trace(output: str) -> dict | None:
        try:
            payload = json.loads(output)
        except Exception:
            return None

        trace_file = payload.get("trace_file")
        if not trace_file:
            return None
        record = {
            "child_task_id": payload.get("child_task_id", ""),
            "trace_file": trace_file,
        }
        if payload.get("success") is not None:
            record["success"] = payload.get("success")
        if payload.get("schema_ok") is not None:
            record["schema_ok"] = payload.get("schema_ok")
        return record
