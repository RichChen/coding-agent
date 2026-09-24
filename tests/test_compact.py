"""Tests for micro-compact Layer 1."""
import pytest
from src.runtime.compact import (
    MicroCompactHooks,
    micro_compact_openai_messages,
    micro_compact_openai_messages_with_stats,
)
from src.runtime.hooks import HookContext


def _make_tool_msg(call_id, content, name="read_file"):
    return {"role": "tool", "tool_call_id": call_id, "content": content}


def _make_assistant_msg(tool_calls):
    return {"role": "assistant", "content": None, "tool_calls": tool_calls}


def _make_tc(call_id, name):
    return {"id": call_id, "type": "function", "function": {"name": name, "arguments": "{}"}}


class TestMicroCompact:
    def test_recent_tool_messages_preserved(self):
        messages = [
            {"role": "system", "content": "You are a coding agent."},
            {"role": "user", "content": "Do something."},
            _make_assistant_msg([_make_tc("c1", "write_file"), _make_tc("c2", "run_command")]),
            _make_tool_msg("c1", "Wrote 10 bytes to a.txt"),
            _make_tool_msg("c2", "x" * 200),
            _make_assistant_msg([_make_tc("c3", "read_file")]),
            _make_tool_msg("c3", "file contents"),
        ]
        result = micro_compact_openai_messages(messages, keep_recent=1)
        # c3 is the most recent, should be preserved
        assert result[6]["content"] == "file contents"
        # c1 and c2 are old but c2 has >100 chars, should be compressed
        assert "Wrote 10 bytes" in result[3]["content"]
        # c2 > 100 chars should be compressed
        assert "[Previous: used run_command]" == result[4]["content"]

    def test_read_file_preserved(self):
        messages = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "task"},
            _make_assistant_msg([_make_tc("c1", "read_file")]),
            _make_tool_msg("c1", "x" * 200, name="read_file"),
            _make_assistant_msg([_make_tc("c2", "run_command")]),
            _make_tool_msg("c2", "y" * 200, name="run_command"),
        ]
        result = micro_compact_openai_messages(messages, keep_recent=0)
        # read_file should be preserved even though old and >100 chars
        assert "x" * 200 == result[3]["content"]
        # run_command should be compressed
        assert "[Previous: used run_command]" == result[5]["content"]

    def test_short_content_not_compressed(self):
        messages = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "task"},
            _make_assistant_msg([_make_tc("c1", "run_command")]),
            _make_tool_msg("c1", "short output", name="run_command"),
        ]
        result = micro_compact_openai_messages(messages, keep_recent=0)
        # Short content (< 100 chars) is kept even for non-preserved tools
        assert result[3]["content"] == "short output"

    def test_total_char_count_decreases(self):
        big = "z" * 500
        messages = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "task"},
            _make_assistant_msg([_make_tc("c1", "run_command")]),
            _make_tool_msg("c1", big, name="run_command"),
            _make_assistant_msg([_make_tc("c2", "write_file")]),
            _make_tool_msg("c2", big, name="write_file"),
            _make_assistant_msg([_make_tc("c3", "list_dir")]),
            _make_tool_msg("c3", big, name="list_dir"),
            _make_assistant_msg([_make_tc("c4", "run_command")]),
            _make_tool_msg("c4", big, name="run_command"),
            _make_assistant_msg([_make_tc("c5", "read_file")]),
            _make_tool_msg("c5", "recent", name="read_file"),
        ]
        before = sum(len(m.get("content", "") or "") for m in messages)
        result = micro_compact_openai_messages(messages, keep_recent=2)
        after = sum(len(m.get("content", "") or "") for m in result)
        assert after < before

    def test_stats_report_compacted_tools_and_chars_saved(self):
        big = "z" * 500
        messages = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "task"},
            _make_assistant_msg([_make_tc("c1", "run_command")]),
            _make_tool_msg("c1", big, name="run_command"),
            _make_assistant_msg([_make_tc("c2", "write_file")]),
            _make_tool_msg("c2", big, name="write_file"),
            _make_assistant_msg([_make_tc("c3", "read_file")]),
            _make_tool_msg("c3", big, name="read_file"),
        ]

        result, stats = micro_compact_openai_messages_with_stats(messages, keep_recent=0)

        assert result is messages
        assert stats.did_compact is True
        assert stats.compacted_tool_count == 1
        assert stats.preserved_tool_count == 2
        assert stats.tool_messages_before == 3
        assert stats.tool_messages_after == 3
        assert stats.chars_saved > 0

    def test_no_tool_messages(self):
        messages = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "task"},
            {"role": "assistant", "content": "Done!"},
        ]
        result = micro_compact_openai_messages(messages)
        assert result == messages

    def test_micro_compact_hooks_class(self):
        hooks = MicroCompactHooks(keep_recent=2)
        assert hooks.keep_recent == 2

        messages = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "task"},
            _make_assistant_msg([_make_tc("c1", "run_command")]),
            _make_tool_msg("c1", "x" * 200, name="run_command"),
            _make_assistant_msg([_make_tc("c2", "run_command")]),
            _make_tool_msg("c2", "y" * 200, name="run_command"),
            _make_assistant_msg([_make_tc("c3", "run_command")]),
            _make_tool_msg("c3", "z" * 200, name="run_command"),
        ]

        import asyncio
        ctx = HookContext(step_number=0)
        result = asyncio.run(hooks.before_llm(messages, ctx))
        # Last 2 preserved
        assert "y" * 200 in result[5]["content"]
        assert "z" * 200 in result[7]["content"]
        # First compressed
        assert "[Previous: used run_command]" == result[3]["content"]
        assert ctx.extra["context_stats"]["did_compact"] is True
        assert ctx.extra["context_stats"]["compacted_tool_count"] == 1

    def test_micro_compact_hooks_record_noop_stats(self):
        hooks = MicroCompactHooks(keep_recent=3)
        messages = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "task"},
        ]

        import asyncio
        ctx = HookContext(step_number=0)
        result = asyncio.run(hooks.before_llm(messages, ctx))

        assert result == messages
        assert ctx.extra["context_stats"]["did_compact"] is False
        assert ctx.extra["context_stats"]["message_count_before"] == 2

    def test_protects_user_task_recent_failure_and_recent_modified_files(self):
        messages = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "original task should stay intact"},
            _make_assistant_msg([_make_tc("c1", "run_command")]),
            _make_tool_msg("c1", "x" * 200, name="run_command"),
            _make_assistant_msg([_make_tc("c2", "run_command")]),
            _make_tool_msg("c2", "Error: command failed\n" + "y" * 200, name="run_command"),
            _make_assistant_msg([_make_tc("c3", "write_file")]),
            _make_tool_msg("c3", "Wrote 200 bytes to changed.py\n" + "z" * 200, name="write_file"),
            _make_assistant_msg([_make_tc("c4", "search_replace")]),
            _make_tool_msg("c4", "Replaced text in helper.py\n" + "q" * 200, name="search_replace"),
        ]

        result, stats = micro_compact_openai_messages_with_stats(messages, keep_recent=0)

        assert result[1]["content"] == "original task should stay intact"
        assert result[3]["content"] == "[Previous: used run_command]"
        assert result[5]["content"].startswith("Error: command failed")
        assert "changed.py" in result[7]["content"]
        assert "helper.py" in result[9]["content"]
        assert stats.compacted_tool_count == 1
        assert stats.preserved_tool_count == 3

    def test_context_policy_builds_micro_compact_hook(self):
        from src.runtime.context import ContextPolicyConfig, build_context_hooks

        config = ContextPolicyConfig.from_runtime_config(
            {"micro_compact": True, "keep_recent_tool_results": 2},
            {"tool_output_max_chars": 1000, "read_file_max_lines": 50},
        )
        hooks = build_context_hooks(config)

        assert isinstance(hooks, MicroCompactHooks)
        assert hooks.keep_recent == 2
        assert config.to_trace_metadata()["l2_llm_summary"] is False

    def test_token_threshold_skips_compact_when_below(self):
        big = "z" * 500
        messages = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "task"},
            _make_assistant_msg([_make_tc("c1", "run_command")]),
            _make_tool_msg("c1", big, name="run_command"),
        ]
        hooks = MicroCompactHooks(keep_recent=0, token_threshold=100_000)

        import asyncio
        ctx = HookContext(step_number=0)
        result = asyncio.run(hooks.before_llm(messages, ctx))

        assert result[3]["content"] == big
        stats = ctx.extra["context_stats"]
        assert stats["did_compact"] is False
        assert stats["estimated_tokens_before"] > 0
        assert stats["estimated_tokens_after"] == stats["estimated_tokens_before"]

    def test_token_threshold_compacts_when_above(self):
        big = "z" * 500
        messages = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "task"},
            _make_assistant_msg([_make_tc("c1", "run_command")]),
            _make_tool_msg("c1", big, name="run_command"),
        ]
        hooks = MicroCompactHooks(keep_recent=0, token_threshold=10)

        import asyncio
        ctx = HookContext(step_number=0)
        result = asyncio.run(hooks.before_llm(messages, ctx))

        assert result[3]["content"] == "[Previous: used run_command]"
        stats = ctx.extra["context_stats"]
        assert stats["did_compact"] is True
        assert stats["estimated_tokens_after"] < stats["estimated_tokens_before"]


class TestEventBus:
    def test_emit_writes_jsonl(self, tmp_path):
        from src.tracing.events import EventBus

        bus = EventBus(output_dir=tmp_path)
        bus.open("test_task")
        bus.emit("run_start", task_id="test_task")
        bus.emit("llm_complete", step=0, has_tool_calls=True)
        bus.emit("run_end", success=True)
        bus.close()

        content = bus.path.read_text()
        lines = content.strip().split("\n")
        assert len(lines) == 3
        assert '"event": "run_start"' in lines[0]
        assert '"event": "llm_complete"' in lines[1]
        assert '"event": "run_end"' in lines[2]

    def test_emit_does_nothing_when_closed(self, tmp_path):
        from src.tracing.events import EventBus

        bus = EventBus(output_dir=tmp_path)
        bus.open("t")
        bus.close()
        # emit after close should not raise
        bus.emit("run_end", success=True)

    def test_events_in_agent_loop(self, tmp_path):
        """EventBus wired into AgentLoop emits run_start/llm_complete/tools_complete/run_end."""
        from src.llm.client import LLMResponse, ToolCall
        from src.policy.budget import Budget
        from src.policy.sandbox import Sandbox
        from src.runtime.loop import AgentLoop
        from src.tools.files import ReadFileTool
        from src.tools.registry import ToolRegistry
        from src.tracing.events import EventBus
        from tests.fixtures.mock_llm import MockLLMClient

        (tmp_path / "f.txt").write_text("data")

        responses = [
            LLMResponse(
                text=None,
                tool_calls=[ToolCall(id="tc1", name="read_file", arguments={"path": "f.txt"})],
                usage={"total_tokens": 50},
            ),
            LLMResponse(text="Done.", tool_calls=[], usage={"total_tokens": 30}),
        ]

        tools = ToolRegistry()
        tools.register(ReadFileTool())

        bus = EventBus(output_dir=tmp_path / "events")
        bus.open("t_event")

        agent = AgentLoop(
            llm=MockLLMClient(responses),
            tools=tools,
            sandbox=Sandbox(workspace_root=tmp_path),
            budget=Budget(max_steps=5, total_timeout_seconds=30, step_timeout_seconds=10),
            enabled_tools=["read_file"],
            event_bus=bus,
        )

        import asyncio
        result = asyncio.run(agent.run("Read f.txt", task_id="t_event"))
        bus.close()

        assert result.success is True

        content = bus.path.read_text()
        assert "run_start" in content
        assert "llm_complete" in content
        assert "tools_complete" in content
        assert "run_end" in content

    def test_llm_stream_events_in_agent_loop(self, tmp_path):
        """When use_llm_stream=True, stream events are written to EventBus."""
        from src.llm.client import LLMResponse, ToolCall
        from src.policy.budget import Budget
        from src.policy.sandbox import Sandbox
        from src.runtime.loop import AgentLoop
        from src.tools.files import ReadFileTool
        from src.tools.registry import ToolRegistry
        from src.tracing.events import EventBus
        from tests.fixtures.mock_llm import MockLLMClient

        (tmp_path / "f.txt").write_text("data")

        responses = [
            LLMResponse(
                text=None,
                tool_calls=[ToolCall(id="tc1", name="read_file", arguments={"path": "f.txt"})],
                usage={"total_tokens": 50},
            ),
            LLMResponse(text="Done.", tool_calls=[], usage={"total_tokens": 30}),
        ]

        tools = ToolRegistry()
        tools.register(ReadFileTool())

        bus = EventBus(output_dir=tmp_path / "events")
        bus.open("t_stream")

        agent = AgentLoop(
            llm=MockLLMClient(responses),
            tools=tools,
            sandbox=Sandbox(workspace_root=tmp_path),
            budget=Budget(max_steps=5, total_timeout_seconds=30, step_timeout_seconds=10),
            enabled_tools=["read_file"],
            event_bus=bus,
            use_llm_stream=True,
        )

        import asyncio
        result = asyncio.run(agent.run("Read f.txt", task_id="t_stream"))
        bus.close()

        assert result.success is True
        content = bus.path.read_text()
        # MockLLMClient is capability=non_streaming: honest single done event, no fake deltas.
        # Real message_delta / tool_call_delta transport is covered in tests/test_llm_streaming.py.
        assert "llm_stream_done" in content
        assert "llm_complete" in content
        assert "capability" in content or "non_streaming" in content or "llm_stream_done" in content

    def test_context_compacted_event_in_agent_loop(self, tmp_path):
        """MicroCompactHooks stats are surfaced through AgentLoop events and result."""
        from src.llm.client import LLMResponse, ToolCall
        from src.policy.budget import Budget
        from src.policy.sandbox import Sandbox
        from src.runtime.compact import MicroCompactHooks
        from src.runtime.loop import AgentLoop
        from src.tools.command import RunCommandTool
        from src.tools.registry import ToolRegistry
        from src.tracing.events import EventBus
        from tests.fixtures.mock_llm import MockLLMClient

        responses = [
            LLMResponse(
                text=None,
                tool_calls=[
                    ToolCall(id="tc1", name="run_command", arguments={"command": "python -c \"print('a' * 200)\""}),
                ],
                usage={"total_tokens": 50},
            ),
            LLMResponse(
                text=None,
                tool_calls=[
                    ToolCall(id="tc2", name="run_command", arguments={"command": "python -c \"print('b' * 200)\""}),
                ],
                usage={"total_tokens": 50},
            ),
            LLMResponse(text="Done.", tool_calls=[], usage={"total_tokens": 30}),
        ]

        tools = ToolRegistry()
        tools.register(RunCommandTool())

        bus = EventBus(output_dir=tmp_path / "events")
        agent = AgentLoop(
            llm=MockLLMClient(responses),
            tools=tools,
            sandbox=Sandbox(workspace_root=tmp_path),
            budget=Budget(max_steps=5, total_timeout_seconds=30, step_timeout_seconds=10),
            enabled_tools=["run_command"],
            hooks=MicroCompactHooks(keep_recent=0),
            event_bus=bus,
        )

        import asyncio
        result = asyncio.run(agent.run("Create long command outputs", task_id="compact_event"))

        assert result.success is True
        assert result.context_events
        assert result.context_events[0]["compacted_tool_count"] >= 1

        content = bus.path.read_text()
        assert '"event": "context_compacted"' in content
        assert '"chars_saved"' in content
