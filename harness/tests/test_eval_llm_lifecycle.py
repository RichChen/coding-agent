"""HP-02: EvalRunner must release owned LLM HTTP clients after each task."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx
import pytest

from src.eval.runner import EvalRunner
from src.llm.client import LLMClient, LLMResponse
from src.policy.budget import Budget
from src.policy.sandbox import Sandbox
from src.runtime.loop import AgentLoop
from src.tools.base import ToolContext
from src.tools.registry import ToolRegistry
from src.tools.subagent import SubagentTaskTool
from tests.fixtures.mock_llm import MockLLMClient


def _chat_ok_response() -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "done"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 1,
                "completion_tokens": 1,
                "total_tokens": 2,
            },
        },
    )


def _make_llm(http: httpx.AsyncClient, *, owns: bool) -> LLMClient:
    return LLMClient(
        base_url="https://eval-lifecycle.test/v1",
        api_key="test-key",
        model="fixture-model",
        timeout_seconds=5.0,
        http_client=http,
        owns_http_client=owns,
        supports_streaming=False,
        trust_env=False,
    )


def _make_agent(llm: LLMClient, workspace: Path) -> AgentLoop:
    return AgentLoop(
        llm=llm,
        tools=ToolRegistry(),
        sandbox=Sandbox(workspace_root=workspace),
        budget=Budget(max_steps=3, total_timeout_seconds=10, step_timeout_seconds=5),
        enabled_tools=[],
        use_llm_stream=False,
    )


def _write_dataset(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "tasks": [
                    {
                        "id": "t1",
                        "description": "say done",
                        "expected": {
                            "type": "keywords_in_answer",
                            "keywords": ["done"],
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )


@pytest.mark.asyncio
async def test_eval_runner_closes_owned_http_client_on_success(tmp_path: Path):
    transport = httpx.MockTransport(lambda request: _chat_ok_response())
    http = httpx.AsyncClient(transport=transport, trust_env=False)
    assert http.is_closed is False

    dataset = tmp_path / "dataset.json"
    _write_dataset(dataset)
    workspace = tmp_path / "ws"
    workspace.mkdir()

    def factory(_config: dict) -> AgentLoop:
        return _make_agent(_make_llm(http, owns=True), workspace)

    runner = EvalRunner(factory, dataset)
    result = await runner._run_task("baseline", {}, runner._load_dataset()[0])

    assert result.success is True
    assert result.final_answer == "done"
    assert http.is_closed is True


@pytest.mark.asyncio
async def test_eval_runner_closes_owned_http_client_on_error(tmp_path: Path):
    transport = httpx.MockTransport(lambda request: _chat_ok_response())
    http = httpx.AsyncClient(transport=transport, trust_env=False)
    dataset = tmp_path / "dataset.json"
    _write_dataset(dataset)
    workspace = tmp_path / "ws"
    workspace.mkdir()

    class BoomLoop(AgentLoop):
        async def run(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("boom during eval")

    def factory(_config: dict) -> AgentLoop:
        return BoomLoop(
            llm=_make_llm(http, owns=True),
            tools=ToolRegistry(),
            sandbox=Sandbox(workspace_root=workspace),
            budget=Budget(max_steps=1, total_timeout_seconds=5, step_timeout_seconds=2),
            enabled_tools=[],
            use_llm_stream=False,
        )

    runner = EvalRunner(factory, dataset)
    with pytest.raises(RuntimeError, match="boom during eval"):
        await runner._run_task("baseline", {}, runner._load_dataset()[0])

    assert http.is_closed is True


@pytest.mark.asyncio
async def test_eval_runner_closes_owned_http_client_on_cancel(tmp_path: Path):
    transport = httpx.MockTransport(lambda request: _chat_ok_response())
    http = httpx.AsyncClient(transport=transport, trust_env=False)
    dataset = tmp_path / "dataset.json"
    _write_dataset(dataset)
    workspace = tmp_path / "ws"
    workspace.mkdir()

    class CancelLoop(AgentLoop):
        async def run(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise asyncio.CancelledError()

    def factory(_config: dict) -> AgentLoop:
        return CancelLoop(
            llm=_make_llm(http, owns=True),
            tools=ToolRegistry(),
            sandbox=Sandbox(workspace_root=workspace),
            budget=Budget(max_steps=1, total_timeout_seconds=5, step_timeout_seconds=2),
            enabled_tools=[],
            use_llm_stream=False,
        )

    runner = EvalRunner(factory, dataset)
    with pytest.raises(asyncio.CancelledError):
        await runner._run_task("baseline", {}, runner._load_dataset()[0])

    assert http.is_closed is True


@pytest.mark.asyncio
async def test_eval_runner_does_not_close_borrowed_http_client(tmp_path: Path):
    transport = httpx.MockTransport(lambda request: _chat_ok_response())
    http = httpx.AsyncClient(transport=transport, trust_env=False)
    dataset = tmp_path / "dataset.json"
    _write_dataset(dataset)
    workspace = tmp_path / "ws"
    workspace.mkdir()

    def factory(_config: dict) -> AgentLoop:
        return _make_agent(_make_llm(http, owns=False), workspace)

    runner = EvalRunner(factory, dataset)
    result = await runner._run_task("baseline", {}, runner._load_dataset()[0])

    assert result.success is True
    assert http.is_closed is False
    await http.aclose()
    assert http.is_closed is True


@pytest.mark.asyncio
async def test_subagent_does_not_close_shared_parent_client(tmp_path: Path):
    """Child AgentLoop shares parent llm; subagent completion must not aclose it."""
    (tmp_path / "a.txt").write_text("data", encoding="utf-8")
    responses = [
        LLMResponse(
            text=(
                "summary: ok\n"
                "findings:\n"
                "- present\n"
                "suggested next steps:\n"
                "- none\n"
                "confidence: high"
            ),
            tool_calls=[],
            usage={"total_tokens": 5},
        ),
    ]
    mock = MockLLMClient(responses)
    aclose_calls: list[str] = []

    async def tracking_aclose() -> None:
        aclose_calls.append("aclose")
        mock._closed = True

    mock.aclose = tracking_aclose  # type: ignore[method-assign]

    tool = SubagentTaskTool(llm=mock, output_dir=tmp_path / "traces", max_steps=2)
    result = await tool.execute(
        {"_call_id": "parent_tc1", "task": "Inspect a.txt"},
        ctx=ToolContext(workspace_root=tmp_path),
    )
    assert result.success is True
    assert aclose_calls == []
    assert mock._closed is False
