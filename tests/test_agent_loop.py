"""AgentLoop integration tests with MockLLMClient.

No API key needed — tests verify the full think→act→observe cycle.
"""

import pytest

from src.llm.client import LLMResponse, ToolCall
from src.policy.budget import Budget
from src.policy.sandbox import Sandbox
from src.runtime.loop import AgentLoop
from src.tools.files import ReadFileTool, WriteFileTool
from src.tools.registry import ToolRegistry
from tests.fixtures.mock_llm import MockLLMClient


def _make_tool_call(call_id, name, args):
    return ToolCall(id=call_id, name=name, arguments=args)


class TestAgentLoopIntegration:
    async def test_single_read_then_answer(self, tmp_path):
        """Agent reads a file then produces a final answer."""
        # Set up workspace
        (tmp_path / "hello.txt").write_text("Hello, World!")

        # Pre-scripted LLM responses
        responses = [
            # Round 1: request to read the file
            LLMResponse(
                text=None,
                tool_calls=[
                    _make_tool_call("tc1", "read_file", {"path": "hello.txt"}),
                ],
                usage={"total_tokens": 100},
            ),
            # Round 2: final answer
            LLMResponse(
                text="The file contains: Hello, World!",
                tool_calls=[],
                finish_reason="stop",
                usage={"total_tokens": 50},
            ),
        ]
        mock_llm = MockLLMClient(responses)

        tools = ToolRegistry()
        tools.register(ReadFileTool())

        sandbox = Sandbox(workspace_root=tmp_path)
        budget = Budget(max_steps=5, total_timeout_seconds=30, step_timeout_seconds=10)

        agent = AgentLoop(
            llm=mock_llm,
            tools=tools,
            sandbox=sandbox,
            budget=budget,
            enabled_tools=["read_file"],
        )

        result = await agent.run("Read hello.txt and tell me what it says", task_id="t1")

        assert result.success is True
        assert result.final_answer == "The file contains: Hello, World!"
        assert len(result.steps) == 2
        assert result.total_tool_invocations == 1
        assert result.tool_failures == 0
        assert result.total_tokens == 150

    async def test_tool_failure_counted(self, tmp_path):
        """Tool errors increment tool_failures but agent keeps running."""
        responses = [
            # Round 1: try to read a nonexistent file
            LLMResponse(
                text=None,
                tool_calls=[
                    _make_tool_call("tc1", "read_file", {"path": "missing.txt"}),
                ],
                usage={"total_tokens": 80},
            ),
            # Round 2: final answer despite failure
            LLMResponse(
                text="File not found, cannot proceed.",
                tool_calls=[],
                finish_reason="stop",
                usage={"total_tokens": 60},
            ),
        ]
        mock_llm = MockLLMClient(responses)

        tools = ToolRegistry()
        tools.register(ReadFileTool())

        sandbox = Sandbox(workspace_root=tmp_path)
        budget = Budget(max_steps=5, total_timeout_seconds=30, step_timeout_seconds=10)

        agent = AgentLoop(
            llm=mock_llm,
            tools=tools,
            sandbox=sandbox,
            budget=budget,
            enabled_tools=["read_file"],
        )

        result = await agent.run("Read missing.txt", task_id="t2")

        assert result.success is True  # agent ended cleanly
        assert result.tool_failures == 1
        assert result.total_tool_invocations == 1
        assert len(result.steps) == 2

    async def test_multi_tool_round(self, tmp_path):
        """Agent calls write_file then read_file in the same round."""
        responses = [
            # Round 1: write then read
            LLMResponse(
                text=None,
                tool_calls=[
                    _make_tool_call("tc1", "write_file", {"path": "out.txt", "content": "data"}),
                    _make_tool_call("tc2", "read_file", {"path": "out.txt"}),
                ],
                usage={"total_tokens": 120},
            ),
            # Round 2: final answer
            LLMResponse(
                text="Written and verified.",
                tool_calls=[],
                finish_reason="stop",
                usage={"total_tokens": 40},
            ),
        ]
        mock_llm = MockLLMClient(responses)

        tools = ToolRegistry()
        tools.register(WriteFileTool())
        tools.register(ReadFileTool())

        sandbox = Sandbox(workspace_root=tmp_path)
        budget = Budget(max_steps=5, total_timeout_seconds=30, step_timeout_seconds=10)

        agent = AgentLoop(
            llm=mock_llm,
            tools=tools,
            sandbox=sandbox,
            budget=budget,
            enabled_tools=["read_file", "write_file"],
        )

        result = await agent.run("Write data and verify", task_id="t3")

        assert result.success is True
        assert result.total_tool_invocations == 2
        assert result.tool_failures == 0
        assert (tmp_path / "out.txt").read_text() == "data"

    async def test_step_number_increments(self, tmp_path):
        """StepRecord.step should be 0, 1, 2, ... across rounds."""
        responses = [
            LLMResponse(
                text=None,
                tool_calls=[_make_tool_call("tc1", "read_file", {"path": "x.txt"})],
                usage={"total_tokens": 50},
            ),
            LLMResponse(
                text=None,
                tool_calls=[_make_tool_call("tc2", "read_file", {"path": "y.txt"})],
                usage={"total_tokens": 50},
            ),
            LLMResponse(
                text="Done.",
                tool_calls=[],
                usage={"total_tokens": 30},
            ),
        ]
        mock_llm = MockLLMClient(responses)

        tools = ToolRegistry()
        tools.register(ReadFileTool())

        sandbox = Sandbox(workspace_root=tmp_path)
        (tmp_path / "x.txt").write_text("x")
        (tmp_path / "y.txt").write_text("y")
        budget = Budget(max_steps=5, total_timeout_seconds=30, step_timeout_seconds=10)

        agent = AgentLoop(
            llm=mock_llm,
            tools=tools,
            sandbox=sandbox,
            budget=budget,
            enabled_tools=["read_file"],
        )

        result = await agent.run("Read two files", task_id="t4")

        assert result.success is True
        assert len(result.steps) == 3
        assert [s.step for s in result.steps] == [0, 1, 2]

    async def test_mock_exhausted_raises(self, tmp_path):
        """When LLM returns more tool_calls than expected, the mock raises."""
        responses = [
            LLMResponse(
                text=None,
                tool_calls=[_make_tool_call("tc1", "read_file", {"path": "a.txt"})],
                usage={"total_tokens": 50},
            ),
            # No second response configured → agent will crash on round 2
        ]
        mock_llm = MockLLMClient(responses)

        tools = ToolRegistry()
        tools.register(ReadFileTool())

        (tmp_path / "a.txt").write_text("a")
        sandbox = Sandbox(workspace_root=tmp_path)
        budget = Budget(max_steps=5, total_timeout_seconds=30, step_timeout_seconds=10)

        agent = AgentLoop(
            llm=mock_llm,
            tools=tools,
            sandbox=sandbox,
            budget=budget,
            enabled_tools=["read_file"],
        )

        result = await agent.run("Read a file", task_id="t5")

        # Agent should fail because second LLM call errors out
        assert result.success is False

    async def test_cancel_event_stops_before_llm(self, tmp_path):
        """Pre-set cancel_event returns CANCELLED without calling LLM."""
        import asyncio

        from src.runtime.loop import FailureReason

        mock_llm = MockLLMClient([
            LLMResponse(text="should not run", tool_calls=[], usage={"total_tokens": 1}),
        ])
        tools = ToolRegistry()
        tools.register(ReadFileTool())
        sandbox = Sandbox(workspace_root=tmp_path)
        budget = Budget(max_steps=5, total_timeout_seconds=30, step_timeout_seconds=10)

        cancel_event = asyncio.Event()
        cancel_event.set()

        agent = AgentLoop(
            llm=mock_llm,
            tools=tools,
            sandbox=sandbox,
            budget=budget,
            enabled_tools=["read_file"],
            cancel_event=cancel_event,
        )

        result = await agent.run("Should cancel immediately", task_id="t_cancel")

        assert result.success is False
        assert result.failure_reason in (
            FailureReason.CANCELLED,
            FailureReason.USER_CANCELLED,
        )
        assert len(mock_llm.calls) == 0
