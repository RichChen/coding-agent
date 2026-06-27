import asyncio

from src.llm.client import LLMResponse, ToolCall
from src.policy.budget import Budget
from src.policy.sandbox import Sandbox
from src.runtime.loop import AgentLoop
from src.runtime.planner import SimplePlanner
from src.tools.files import ReadFileTool
from src.tools.registry import ToolRegistry
from src.tracing.events import EventBus
from tests.fixtures.mock_llm import MockLLMClient


def _make_tool_call(call_id, name, args):
    return ToolCall(id=call_id, name=name, arguments=args)


def test_plan_act_mode_returns_completed_plan_sync(tmp_path):
    responses = [
        LLMResponse(
            text=None,
            tool_calls=[_make_tool_call("tc1", "read_file", {"path": "a.txt"})],
            usage={"total_tokens": 50},
        ),
        LLMResponse(text="Done.", tool_calls=[], usage={"total_tokens": 30}),
    ]
    (tmp_path / "a.txt").write_text("a")

    tools = ToolRegistry()
    tools.register(ReadFileTool())

    mock_llm = MockLLMClient(responses)
    agent = AgentLoop(
        llm=mock_llm,
        tools=tools,
        sandbox=Sandbox(workspace_root=tmp_path),
        budget=Budget(max_steps=5, total_timeout_seconds=30, step_timeout_seconds=10),
        enabled_tools=["read_file"],
        runtime_mode="plan_act",
        planner=SimplePlanner(),
    )

    result = asyncio.run(agent.run("Read a file", task_id="plan_task"))

    assert result.success is True
    assert result.plan is not None
    assert result.plan["goal"] == "Read a file"
    assert all(step["status"] == "done" for step in result.plan["steps"])
    assert "Current execution plan" in mock_llm.calls[0]["messages"][2]["content"]


def test_react_mode_has_no_plan_by_default_sync(tmp_path):
    agent = AgentLoop(
        llm=MockLLMClient([
            LLMResponse(text="Done.", tool_calls=[], usage={"total_tokens": 10}),
        ]),
        tools=ToolRegistry(),
        sandbox=Sandbox(workspace_root=tmp_path),
        budget=Budget(max_steps=5, total_timeout_seconds=30, step_timeout_seconds=10),
    )

    result = asyncio.run(agent.run("Answer directly", task_id="react_task"))

    assert result.success is True
    assert result.plan is None


def test_plan_act_replans_once_after_tool_failure_sync(tmp_path):
    responses = [
        LLMResponse(
            text=None,
            tool_calls=[_make_tool_call("tc1", "read_file", {"path": "missing.txt"})],
            usage={"total_tokens": 50},
        ),
        LLMResponse(
            text=None,
            tool_calls=[_make_tool_call("tc2", "read_file", {"path": "a.txt"})],
            usage={"total_tokens": 50},
        ),
        LLMResponse(text="Done.", tool_calls=[], usage={"total_tokens": 30}),
    ]
    (tmp_path / "a.txt").write_text("a")

    tools = ToolRegistry()
    tools.register(ReadFileTool())

    bus = EventBus(output_dir=tmp_path / "events")
    agent = AgentLoop(
        llm=MockLLMClient(responses),
        tools=tools,
        sandbox=Sandbox(workspace_root=tmp_path),
        budget=Budget(max_steps=5, total_timeout_seconds=30, step_timeout_seconds=10),
        enabled_tools=["read_file"],
        runtime_mode="plan_act",
        planner=SimplePlanner(),
        event_bus=bus,
    )

    result = asyncio.run(agent.run("Read a file", task_id="plan_replan_task"))

    assert result.success is True
    assert any("Re-inspect relevant files after the tool failure" in step["title"] for step in result.plan["steps"])
    content = bus.path.read_text(encoding="utf-8")
    assert '"event": "plan_replanned"' in content


def test_plan_act_appends_plan_update_message_after_advance_sync(tmp_path):
    responses = [
        LLMResponse(
            text=None,
            tool_calls=[_make_tool_call("tc1", "read_file", {"path": "a.txt"})],
            usage={"total_tokens": 50},
        ),
        LLMResponse(text="Done.", tool_calls=[], usage={"total_tokens": 30}),
    ]
    (tmp_path / "a.txt").write_text("a")

    tools = ToolRegistry()
    tools.register(ReadFileTool())

    mock_llm = MockLLMClient(responses)
    agent = AgentLoop(
        llm=mock_llm,
        tools=tools,
        sandbox=Sandbox(workspace_root=tmp_path),
        budget=Budget(max_steps=5, total_timeout_seconds=30, step_timeout_seconds=10),
        enabled_tools=["read_file"],
        runtime_mode="plan_act",
        planner=SimplePlanner(),
    )

    asyncio.run(agent.run("Read a file", task_id="plan_update_task"))

    plan_update_msgs = [
        m
        for m in mock_llm.calls[1]["messages"]
        if m.get("role") == "system" and m.get("content", "").startswith("Plan update:")
    ]
    assert len(plan_update_msgs) >= 1
