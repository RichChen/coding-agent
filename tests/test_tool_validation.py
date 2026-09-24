"""HP-01: strict tool argument parsing and batch dispatch gate."""

from __future__ import annotations

import pytest

from src.llm.client import LLMClient, LLMError, LLMErrorKind, LLMResponse, ToolCall
from src.policy.budget import Budget
from src.policy.sandbox import Sandbox
from src.runtime.loop import AgentLoop
from src.tools.base import SideEffectClass, Tool, ToolContext, ToolResult, ToolStatus
from src.tools.files import ReadFileTool, WriteFileTool
from src.tools.registry import ToolRegistry
from src.tools.validation import (
    DEFAULT_MAX_ARGUMENT_BYTES,
    ToolValidationErrorKind,
    parse_tool_arguments_json,
    validate_tool_call_batch,
)
from tests.fixtures.mock_llm import MockLLMClient


class SpyTool(Tool):
    name = "spy_tool"
    description = "Spy tool that records executions."
    side_effect = SideEffectClass.NON_IDEMPOTENT
    parameters = {
        "type": "object",
        "properties": {
            "value": {"type": "string"},
        },
        "required": ["value"],
        "additionalProperties": False,
    }

    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def execute(self, params: dict, ctx: ToolContext) -> ToolResult:
        self.calls.append({"params": dict(params), "call_id": ctx.call_id})
        return ToolResult(
            call_id=ctx.call_id,
            name=self.name,
            success=True,
            output=f"spied:{params.get('value')}",
        )


def _client() -> LLMClient:
    return LLMClient(base_url="https://unused.invalid/v1", api_key="fake", model="fixture")


def _tool_response(*raw_calls: dict) -> dict:
    return {
        "choices": [
            {
                "message": {"content": None, "tool_calls": list(raw_calls)},
                "finish_reason": "tool_calls",
            }
        ],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
    }


class TestStrictArgumentParsing:
    def test_invalid_json_does_not_become_empty_object(self):
        """Behavior counterexample: old code coerced '{' to {}."""
        client = _client()
        response = client._parse_response(
            _tool_response(
                {
                    "id": "t1",
                    "function": {"name": "write_file", "arguments": "{"},
                }
            )
        )
        assert response.tool_calls[0].arguments is None
        assert response.tool_calls[0].arguments != {}
        assert response.tool_calls[0].parse_error is not None
        assert response.tool_calls[0].parse_error.kind == ToolValidationErrorKind.INVALID_JSON

    @pytest.mark.parametrize(
        "raw,kind",
        [
            ("null", ToolValidationErrorKind.NOT_OBJECT),
            ("[]", ToolValidationErrorKind.NOT_OBJECT),
            ("1", ToolValidationErrorKind.NOT_OBJECT),
            ('"str"', ToolValidationErrorKind.NOT_OBJECT),
        ],
    )
    def test_non_object_json_rejected(self, raw, kind):
        client = _client()
        response = client._parse_response(
            _tool_response(
                {"id": "t1", "function": {"name": "write_file", "arguments": raw}}
            )
        )
        assert response.tool_calls[0].arguments is None
        assert response.tool_calls[0].parse_error.kind == kind

    def test_missing_id_raises_parse_error(self):
        client = _client()
        with pytest.raises(LLMError) as exc:
            client._parse_response(
                _tool_response(
                    {"function": {"name": "write_file", "arguments": '{"path":"a"}'}}
                )
            )
        assert exc.value.kind == LLMErrorKind.PARSE

    def test_missing_function_raises_parse_error(self):
        client = _client()
        with pytest.raises(LLMError) as exc:
            client._parse_response(_tool_response({"id": "t1"}))
        assert exc.value.kind == LLMErrorKind.PARSE

    def test_oversized_arguments_rejected_before_json_parse(self):
        huge = "{" + ("a" * (DEFAULT_MAX_ARGUMENT_BYTES + 10))
        parsed = parse_tool_arguments_json(
            call_id="t1",
            name="write_file",
            raw_arguments=huge,
            max_argument_bytes=DEFAULT_MAX_ARGUMENT_BYTES,
        )
        assert parsed.arguments is None
        assert parsed.error is not None
        assert parsed.error.kind == ToolValidationErrorKind.TOO_LARGE

    def test_valid_object_preserved_without_type_coercion(self):
        client = _client()
        response = client._parse_response(
            _tool_response(
                {
                    "id": "t1",
                    "function": {
                        "name": "read_file",
                        "arguments": '{"path": "a.txt", "limit": 3}',
                    },
                }
            )
        )
        assert response.tool_calls[0].arguments == {"path": "a.txt", "limit": 3}
        assert response.tool_calls[0].parse_error is None


class TestBatchDispatchGate:
    @pytest.mark.asyncio
    async def test_invalid_json_executes_zero_tools(self, tmp_path):
        spy = SpyTool()
        registry = ToolRegistry()
        registry.register(spy)

        client = _client()
        parsed = client._parse_response(
            _tool_response(
                {
                    "id": "bad",
                    "function": {"name": "spy_tool", "arguments": "{"},
                }
            )
        )
        mock = MockLLMClient(
            [
                parsed,
                LLMResponse(text="done", tool_calls=[], usage={"total_tokens": 1}),
            ]
        )
        agent = AgentLoop(
            llm=mock,
            tools=registry,
            sandbox=Sandbox(workspace_root=tmp_path),
            budget=Budget(max_steps=5, total_timeout_seconds=30, step_timeout_seconds=10),
            enabled_tools=["spy_tool"],
        )
        result = await agent.run("call spy", task_id="hp01-invalid-json")

        assert len(spy.calls) == 0
        assert result.total_tool_invocations == 0
        assert result.success is True  # recovered with final answer
        assert result.tool_failures >= 1
        assert "invalid_json" in result.steps[0].tool_results[0]["error_kind"]

    @pytest.mark.asyncio
    async def test_schema_and_reserved_field_block_execution(self, tmp_path):
        spy = SpyTool()
        registry = ToolRegistry()
        registry.register(spy)
        registry.register(ReadFileTool())

        responses = [
            LLMResponse(
                tool_calls=[
                    ToolCall(id="missing", name="spy_tool", arguments={}),
                    ToolCall(
                        id="reserved",
                        name="read_file",
                        arguments={"path": "a.txt", "_call_id": "injected"},
                    ),
                    ToolCall(id="badtype", name="spy_tool", arguments={"value": 123}),
                ],
                usage={"total_tokens": 1},
            ),
            LLMResponse(text="ok", tool_calls=[], usage={"total_tokens": 1}),
        ]
        agent = AgentLoop(
            llm=MockLLMClient(responses),
            tools=registry,
            sandbox=Sandbox(workspace_root=tmp_path),
            budget=Budget(max_steps=5, total_timeout_seconds=30, step_timeout_seconds=10),
            enabled_tools=["spy_tool", "read_file"],
        )
        result = await agent.run("bad schemas", task_id="hp01-schema")

        assert len(spy.calls) == 0
        assert result.total_tool_invocations == 0
        kinds = {r["error_kind"] for r in result.steps[0].tool_results}
        assert "schema" in kinds or "reserved_field" in kinds or "batch_blocked" in kinds

    @pytest.mark.asyncio
    async def test_registered_but_disabled_tool_blocked(self, tmp_path):
        spy = SpyTool()
        registry = ToolRegistry()
        registry.register(spy)
        registry.register(ReadFileTool())

        # Schema list only exposes read_file, but fake provider ignores that.
        responses = [
            LLMResponse(
                tool_calls=[
                    ToolCall(id="tc1", name="spy_tool", arguments={"value": "x"}),
                ],
                usage={"total_tokens": 1},
            ),
            LLMResponse(text="done", tool_calls=[], usage={"total_tokens": 1}),
        ]
        agent = AgentLoop(
            llm=MockLLMClient(responses),
            tools=registry,
            sandbox=Sandbox(workspace_root=tmp_path),
            budget=Budget(max_steps=5, total_timeout_seconds=30, step_timeout_seconds=10),
            enabled_tools=["read_file"],
        )
        result = await agent.run("disabled spy", task_id="hp01-disabled")

        assert len(spy.calls) == 0
        assert result.total_tool_invocations == 0
        assert result.steps[0].tool_results[0]["error_kind"] == "tool_disabled"

    @pytest.mark.asyncio
    async def test_unknown_tool_blocked(self, tmp_path):
        registry = ToolRegistry()
        registry.register(ReadFileTool())
        responses = [
            LLMResponse(
                tool_calls=[
                    ToolCall(id="tc1", name="not_a_tool", arguments={"path": "a"}),
                ],
                usage={"total_tokens": 1},
            ),
            LLMResponse(text="done", tool_calls=[], usage={"total_tokens": 1}),
        ]
        agent = AgentLoop(
            llm=MockLLMClient(responses),
            tools=registry,
            sandbox=Sandbox(workspace_root=tmp_path),
            budget=Budget(max_steps=5, total_timeout_seconds=30, step_timeout_seconds=10),
            enabled_tools=["read_file"],
        )
        result = await agent.run("unknown", task_id="hp01-unknown")
        assert result.total_tool_invocations == 0
        assert result.steps[0].tool_results[0]["error_kind"] == "unknown_tool"

    @pytest.mark.asyncio
    async def test_batch_blocks_all_when_one_invalid(self, tmp_path):
        spy = SpyTool()
        write = WriteFileTool()
        registry = ToolRegistry()
        registry.register(spy)
        registry.register(write)

        responses = [
            LLMResponse(
                tool_calls=[
                    ToolCall(id="good", name="spy_tool", arguments={"value": "ok"}),
                    ToolCall(id="bad", name="write_file", arguments={"path": "x.txt"}),
                ],
                usage={"total_tokens": 1},
            ),
            LLMResponse(text="recovered", tool_calls=[], usage={"total_tokens": 1}),
        ]
        agent = AgentLoop(
            llm=MockLLMClient(responses),
            tools=registry,
            sandbox=Sandbox(workspace_root=tmp_path),
            budget=Budget(max_steps=5, total_timeout_seconds=30, step_timeout_seconds=10),
            enabled_tools=["spy_tool", "write_file"],
        )
        result = await agent.run("batch", task_id="hp01-batch")

        assert len(spy.calls) == 0
        assert not (tmp_path / "x.txt").exists()
        assert result.total_tool_invocations == 0
        error_kinds = [r["error_kind"] for r in result.steps[0].tool_results]
        assert "schema" in error_kinds
        assert "batch_blocked" in error_kinds

    @pytest.mark.asyncio
    async def test_valid_read_write_compatible_and_no_call_id_pollution(self, tmp_path):
        registry = ToolRegistry()
        registry.register(WriteFileTool())
        registry.register(ReadFileTool())

        responses = [
            LLMResponse(
                tool_calls=[
                    ToolCall(
                        id="w1",
                        name="write_file",
                        arguments={"path": "out.txt", "content": "hello"},
                    ),
                    ToolCall(id="r1", name="read_file", arguments={"path": "out.txt"}),
                ],
                usage={"total_tokens": 2},
            ),
            LLMResponse(text="done", tool_calls=[], usage={"total_tokens": 1}),
        ]
        agent = AgentLoop(
            llm=MockLLMClient(responses),
            tools=registry,
            sandbox=Sandbox(workspace_root=tmp_path),
            budget=Budget(max_steps=5, total_timeout_seconds=30, step_timeout_seconds=10),
            enabled_tools=["read_file", "write_file"],
        )
        result = await agent.run("rw", task_id="hp01-rw")

        assert result.success is True
        assert result.total_tool_invocations == 2
        assert (tmp_path / "out.txt").read_text(encoding="utf-8") == "hello"
        # Host id must not pollute traced original arguments.
        for recorded in result.steps[0].tool_calls:
            assert recorded["args"] is not None
            assert "_call_id" not in recorded["args"]
        # Messages keep tool_call_id pairing.
        # final step is answer; first acting step has two results
        assert [r["success"] for r in result.steps[0].tool_results] == [True, True]

    @pytest.mark.asyncio
    async def test_nonzero_exit_is_not_validation_error(self, tmp_path):
        from src.tools.command import RunCommandTool

        registry = ToolRegistry()
        registry.register(RunCommandTool())
        responses = [
            LLMResponse(
                tool_calls=[
                    ToolCall(
                        id="c1",
                        name="run_command",
                        arguments={
                            "argv": [
                                "python",
                                "-c",
                                "raise SystemExit(7)",
                            ]
                        },
                    )
                ],
                usage={"total_tokens": 1},
            ),
            LLMResponse(text="command finished", tool_calls=[], usage={"total_tokens": 1}),
        ]
        agent = AgentLoop(
            llm=MockLLMClient(responses),
            tools=registry,
            sandbox=Sandbox(workspace_root=tmp_path),
            budget=Budget(max_steps=5, total_timeout_seconds=30, step_timeout_seconds=10),
            enabled_tools=["run_command"],
        )
        result = await agent.run("exit nonzero", task_id="hp01-exit")

        assert result.total_tool_invocations == 1
        tr = result.steps[0].tool_results[0]
        assert tr["success"] is False
        # HP-03 maps nonzero process exit to execution error_kind, not validation.
        assert tr["error_kind"] == "nonzero_exit"
        assert tr["status"] == ToolStatus.FAILED.value
        assert tr["error_kind"] != "invalid_type"


class TestValidationHelpers:
    def test_run_command_mutual_exclusion(self):
        registry = ToolRegistry()
        from src.tools.command import RunCommandTool

        registry.register(RunCommandTool())
        batch = validate_tool_call_batch(
            [
                ToolCall(
                    id="both",
                    name="run_command",
                    arguments={"command": "echo hi", "argv": ["echo", "hi"]},
                )
            ],
            registry=registry,
            enabled_tools=["run_command"],
        )
        assert batch.ok is False
        assert batch.failures[0].kind == ToolValidationErrorKind.TOOL_CONSTRAINT

    def test_side_effect_declarations(self):
        assert ReadFileTool.side_effect == SideEffectClass.READ_ONLY
        assert WriteFileTool.side_effect == SideEffectClass.IDEMPOTENT_WRITE
        from src.tools.command import RunCommandTool

        assert RunCommandTool.side_effect == SideEffectClass.NON_IDEMPOTENT

    def test_tool_result_status_mapping(self):
        ok = ToolResult(call_id="a", name="t", success=True, output="x")
        assert ok.status == ToolStatus.SUCCEEDED
        blocked = ToolResult(
            call_id="b",
            name="t",
            success=False,
            output="",
            error="nope",
            status=ToolStatus.BLOCKED,
            error_kind="schema",
        )
        assert blocked.success is False
        assert blocked.status == ToolStatus.BLOCKED
        assert "Error:" in blocked.to_message()["content"]
