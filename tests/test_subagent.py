import asyncio
import json

from src.harness.factory import build_agent, load_config
from src.llm.client import LLMResponse, ToolCall
from src.policy.budget import Budget
from src.policy.sandbox import Sandbox
from src.runtime.loop import AgentLoop
from src.tools.base import ToolContext
from src.tools.files import ReadFileTool
from src.tools.registry import ToolRegistry
from src.tools.subagent import SubagentTaskTool
from src.tracing.events import EventBus
from src.tracing.logger import TraceLogger
from src.tracing.models import TraceRun
from tests.fixtures.mock_llm import MockLLMClient


def _make_tool_call(call_id, name, args):
    return ToolCall(id=call_id, name=name, arguments=args)


def test_subagent_task_tool_runs_readonly_child_and_writes_trace(tmp_path):
    (tmp_path / "a.txt").write_text("important data")
    responses = [
        LLMResponse(
            text=None,
            tool_calls=[_make_tool_call("child_tc1", "read_file", {"path": "a.txt"})],
            usage={"total_tokens": 20},
        ),
        LLMResponse(
            text=(
                "summary: a.txt contains important data\n"
                "findings:\n"
                "- Data file is present\n"
                "suggested next steps:\n"
                "- Keep the file unchanged\n"
                "confidence: high"
            ),
            tool_calls=[],
            usage={"total_tokens": 10},
        ),
    ]
    tool = SubagentTaskTool(
        llm=MockLLMClient(responses),
        output_dir=tmp_path / "traces",
        max_steps=3,
    )

    result = asyncio.run(
        tool.execute(
            {"_call_id": "parent_tc1", "task": "Inspect a.txt"},
            ctx=ToolContext(workspace_root=tmp_path),
        )
    )

    assert result.success is True
    payload = json.loads(result.output)
    assert payload["success"] is True
    assert payload["files_inspected"] == ["a.txt"]
    assert payload["trace_file"]
    assert payload["child_task_id"].startswith("subagent_")
    assert payload["findings"] == ["Data file is present"]
    assert payload["suggested_next_steps"] == ["Keep the file unchanged"]
    assert payload["confidence"] == "high"
    assert payload["schema_ok"] is True
    assert (tmp_path / "traces").exists()
    assert payload["summary"] == "a.txt contains important data"


def test_parent_agent_can_delegate_to_readonly_subagent(tmp_path):
    (tmp_path / "a.txt").write_text("important data")
    responses = [
        LLMResponse(
            text=None,
            tool_calls=[
                _make_tool_call(
                    "parent_tc1",
                    "subagent_task",
                    {"task": "Read a.txt and summarize it."},
                )
            ],
            usage={"total_tokens": 50},
        ),
        LLMResponse(
            text=None,
            tool_calls=[_make_tool_call("child_tc1", "read_file", {"path": "a.txt"})],
            usage={"total_tokens": 20},
        ),
        LLMResponse(
            text=(
                "summary: a.txt contains important data\n"
                "findings:\n"
                "- Data file is present\n"
                "suggested next steps:\n"
                "- Keep the file unchanged\n"
                "confidence: high"
            ),
            tool_calls=[],
            usage={"total_tokens": 10},
        ),
        LLMResponse(
            text="Delegated analysis complete.",
            tool_calls=[],
            usage={"total_tokens": 30},
        ),
    ]
    llm = MockLLMClient(responses)

    tools = ToolRegistry()
    tools.register(ReadFileTool())
    tools.register(
        SubagentTaskTool(
            llm=llm,
            output_dir=tmp_path / "traces",
            max_steps=3,
        )
    )
    bus = EventBus(output_dir=tmp_path / "events")
    tracer = TraceLogger(output_dir=tmp_path / "parent_traces")

    agent = AgentLoop(
        llm=llm,
        tools=tools,
        sandbox=Sandbox(workspace_root=tmp_path),
        budget=Budget(max_steps=5, total_timeout_seconds=30, step_timeout_seconds=10),
        enabled_tools=["read_file", "subagent_task"],
        event_bus=bus,
        tracer=tracer,
    )

    tracer.open_run("parent_task", config_name="test")
    result = asyncio.run(agent.run("Delegate a readonly analysis.", task_id="parent_task"))
    trace = TraceRun(
        task_id="parent_task",
        config_name="test",
        steps=result.steps,
        success=result.success,
        final_answer=result.final_answer,
        failure_reason=result.failure_reason.value,
        metadata={"subagent_traces": result.subagent_traces},
    )
    tracer.log_run(trace)
    tracer.close()

    assert result.success is True
    assert result.total_tool_invocations == 1
    assert result.steps[0].tool_results[0]["name"] == "subagent_task"

    payload = json.loads(result.steps[0].tool_results[0]["output"])
    assert payload["trace_file"]
    assert payload["files_inspected"] == ["a.txt"]
    assert result.subagent_traces == [
        {
            "child_task_id": payload["child_task_id"],
            "trace_file": payload["trace_file"],
            "success": True,
            "schema_ok": True,
        }
    ]

    events = bus.path.read_text(encoding="utf-8")
    assert '"event": "subagent_completed"' in events
    parent_trace = tracer.path.read_text(encoding="utf-8")
    assert '"subagent_traces"' in parent_trace
    assert "subagent_" in parent_trace
    assert "parent_tc1" in parent_trace


def test_subagent_child_missing_schema_fields_marks_schema_ok_false(tmp_path):
    responses = [
        LLMResponse(
            text=None,
            tool_calls=[_make_tool_call("child_tc1", "read_file", {"path": "a.txt"})],
            usage={"total_tokens": 20},
        ),
        LLMResponse(text="", tool_calls=[], usage={"total_tokens": 10}),
    ]
    tool = SubagentTaskTool(
        llm=MockLLMClient(responses),
        output_dir=tmp_path / "traces",
        max_steps=3,
    )

    result = asyncio.run(
        tool.execute(
            {"_call_id": "parent_tc1", "task": "Inspect a.txt"},
            ctx=ToolContext(workspace_root=tmp_path),
        )
    )

    payload = json.loads(result.output)
    assert payload["schema_ok"] is False


def test_subagent_summary_without_findings_marks_schema_ok_false(tmp_path):
    responses = [
        LLMResponse(
            text=None,
            tool_calls=[_make_tool_call("child_tc1", "read_file", {"path": "a.txt"})],
            usage={"total_tokens": 20},
        ),
        LLMResponse(
            text="summary: only a summary line with no findings section",
            tool_calls=[],
            usage={"total_tokens": 10},
        ),
    ]
    (tmp_path / "a.txt").write_text("data")
    tool = SubagentTaskTool(
        llm=MockLLMClient(responses),
        output_dir=tmp_path / "traces",
        max_steps=3,
    )

    result = asyncio.run(
        tool.execute(
            {"_call_id": "parent_tc1", "task": "Inspect a.txt"},
            ctx=ToolContext(workspace_root=tmp_path),
        )
    )

    payload = json.loads(result.output)
    assert payload["schema_ok"] is False
    assert payload["findings"] == ["only a summary line with no findings section"]


def test_subagent_config_builds_agent_with_tool(tmp_path):
    config = load_config("configs/subagent_readonly.yaml")
    agent = build_agent(config, tmp_path)

    assert "subagent_task" in agent.tools.names()
    assert config["runtime"]["subagents"]["enabled"] is True
    assert config["runtime"]["subagents"]["max_depth"] == 1
    assert config["runtime"]["subagents"]["readonly"] is True
