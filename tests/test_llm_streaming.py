"""HP-02: real SSE streaming gateway, client lifecycle, and retry semantics."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import httpx
import pytest

from src.llm.client import (
    LLMClient,
    LLMError,
    LLMErrorKind,
    LLMResponse,
    LLMStreamEvent,
    StreamCapability,
    normalize_usage,
)
from src.llm.stream import OpenAIStreamAggregator, StreamFailKind
from src.policy.budget import Budget
from src.policy.sandbox import Sandbox
from src.runtime.loop import AgentLoop, FailureReason
from src.runtime.retry import RetryConfig, RetryPolicy
from src.tools.base import SideEffectClass, Tool, ToolContext, ToolResult
from src.tools.files import ReadFileTool, WriteFileTool
from src.tools.registry import ToolRegistry
from src.tools.validation import DEFAULT_MAX_ARGUMENT_BYTES

# Bounded fixture/server cleanup — must fail the test rather than hang pytest.
CLEANUP_TIMEOUT_S = 3.0
GATE_WAIT_TIMEOUT_S = 2.0
_CONN_ERRORS = (
    ConnectionResetError,
    BrokenPipeError,
    ConnectionAbortedError,
    asyncio.IncompleteReadError,
    OSError,
)


# ---------------------------------------------------------------------------
# Loopback SSE fixture — real asyncio TCP + HTTP/1.1 chunked SSE
# ---------------------------------------------------------------------------


@dataclass
class StreamScenario:
    chunks: list[bytes] = field(default_factory=list)
    status: int = 200
    gate_after_first_data: bool = False
    fail_mode: str | None = None
    release_event: asyncio.Event = field(default_factory=asyncio.Event)
    first_data_sent: asyncio.Event = field(default_factory=asyncio.Event)
    request_count: int = 0
    handler_done: asyncio.Event = field(default_factory=asyncio.Event)


async def _read_http_request(reader: asyncio.StreamReader) -> bytes:
    header = await reader.readuntil(b"\r\n\r\n")
    length = 0
    for line in header.split(b"\r\n"):
        if line.lower().startswith(b"content-length:"):
            length = int(line.split(b":", 1)[1].strip())
    body = await reader.readexactly(length) if length else b""
    return header + body


def _chunked(data: bytes) -> bytes:
    return f"{len(data):x}\r\n".encode("ascii") + data + b"\r\n"


async def _safe_drain(writer: asyncio.StreamWriter) -> bool:
    """Drain or return False if the peer already closed."""
    if writer.is_closing():
        return False
    try:
        await writer.drain()
        return True
    except _CONN_ERRORS:
        return False


async def _write_sse_response(
    writer: asyncio.StreamWriter,
    scenario: StreamScenario,
) -> None:
    scenario.request_count += 1
    scenario.handler_done = asyncio.Event()
    mode = scenario.fail_mode
    count = scenario.request_count

    try:
        if mode == "400":
            body = b'{"error":"bad request"}'
            writer.write(
                b"HTTP/1.1 400 Bad Request\r\n"
                b"Content-Type: application/json\r\n"
                b"Content-Length: " + str(len(body)).encode() + b"\r\n"
                b"Connection: close\r\n\r\n" + body
            )
            await _safe_drain(writer)
            return
        if mode == "429_then_ok" and count == 1:
            body = b'{"error":"rate limit"}'
            writer.write(
                b"HTTP/1.1 429 Too Many Requests\r\n"
                b"Content-Type: application/json\r\n"
                b"Content-Length: " + str(len(body)).encode() + b"\r\n"
                b"Connection: close\r\n\r\n" + body
            )
            await _safe_drain(writer)
            return
        if mode == "503_then_ok" and count == 1:
            body = b'{"error":"unavailable"}'
            writer.write(
                b"HTTP/1.1 503 Service Unavailable\r\n"
                b"Content-Type: application/json\r\n"
                b"Content-Length: " + str(len(body)).encode() + b"\r\n"
                b"Connection: close\r\n\r\n" + body
            )
            await _safe_drain(writer)
            return
        if mode == "drop":
            writer.write(
                b"HTTP/1.1 200 OK\r\n"
                b"Content-Type: text/event-stream\r\n"
                b"Transfer-Encoding: chunked\r\n"
                b"Connection: close\r\n\r\n"
            )
            if not await _safe_drain(writer):
                return
            writer.write(_chunked(_content_chunk("partial")))
            if not await _safe_drain(writer):
                return
            writer.write(b"0\r\n\r\n")
            await _safe_drain(writer)
            return

        writer.write(
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: text/event-stream\r\n"
            b"Cache-Control: no-cache\r\n"
            b"Transfer-Encoding: chunked\r\n"
            b"Connection: close\r\n\r\n"
        )
        if not await _safe_drain(writer):
            return

        for i, chunk in enumerate(scenario.chunks):
            if writer.is_closing():
                return
            try:
                writer.write(_chunked(chunk))
            except _CONN_ERRORS:
                return
            if not await _safe_drain(writer):
                return
            if scenario.gate_after_first_data and i == 0 and chunk.startswith(b"data:"):
                scenario.first_data_sent.set()
                try:
                    await asyncio.wait_for(
                        scenario.release_event.wait(), timeout=GATE_WAIT_TIMEOUT_S
                    )
                except asyncio.TimeoutError:
                    return

        if writer.is_closing():
            return
        try:
            writer.write(b"0\r\n\r\n")
        except _CONN_ERRORS:
            return
        await _safe_drain(writer)
    finally:
        scenario.handler_done.set()


@pytest.fixture
async def sse_server():
    scenario = StreamScenario()
    active_handlers: set[asyncio.Task] = set()
    writers: set[asyncio.StreamWriter] = set()

    async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        task = asyncio.current_task()
        if task is not None:
            active_handlers.add(task)
        writers.add(writer)
        try:
            await _read_http_request(reader)
            await _write_sse_response(writer, scenario)
        except asyncio.CancelledError:
            raise
        except _CONN_ERRORS:
            pass
        except Exception:
            pass
        finally:
            try:
                if not writer.is_closing():
                    writer.close()
                await asyncio.wait_for(writer.wait_closed(), timeout=1.0)
            except Exception:
                pass
            writers.discard(writer)
            if task is not None:
                active_handlers.discard(task)

    server = await asyncio.start_server(handle, "127.0.0.1", 0)
    sockets = server.sockets or []
    port = sockets[0].getsockname()[1]
    base_url = f"http://127.0.0.1:{port}/v1"

    def configure(
        chunks: list[bytes],
        *,
        gate_after_first_data: bool = False,
        fail_mode: str | None = None,
        reset_count: bool = True,
    ) -> StreamScenario:
        scenario.chunks = list(chunks)
        scenario.gate_after_first_data = gate_after_first_data
        scenario.fail_mode = fail_mode
        scenario.release_event = asyncio.Event()
        scenario.first_data_sent = asyncio.Event()
        scenario.handler_done = asyncio.Event()
        if reset_count:
            scenario.request_count = 0
        return scenario

    try:
        yield base_url, configure, scenario
    finally:
        # Unblock any gated handler before cancelling.
        scenario.release_event.set()
        for w in list(writers):
            try:
                if not w.is_closing():
                    w.close()
            except Exception:
                pass
        for t in list(active_handlers):
            t.cancel()
        if active_handlers:
            done, pending = await asyncio.wait(
                list(active_handlers), timeout=CLEANUP_TIMEOUT_S
            )
            if pending:
                pytest.fail(
                    f"sse_server handler tasks did not finish within {CLEANUP_TIMEOUT_S}s: "
                    f"{len(pending)} still pending"
                )
        server.close()
        try:
            await asyncio.wait_for(server.wait_closed(), timeout=CLEANUP_TIMEOUT_S)
        except asyncio.TimeoutError:
            pytest.fail(
                f"sse_server.wait_closed exceeded cleanup timeout {CLEANUP_TIMEOUT_S}s"
            )


def _sse_json(obj: dict[str, Any]) -> bytes:
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n".encode("utf-8")


def _content_chunk(text: str) -> bytes:
    return _sse_json({"choices": [{"index": 0, "delta": {"content": text}}]})


def _tool_chunk(
    *,
    index: int,
    call_id: str | None = None,
    name: str | None = None,
    arguments: str | None = None,
    finish_reason: str | None = None,
) -> bytes:
    tc: dict[str, Any] = {"index": index}
    if call_id is not None:
        tc["id"] = call_id
        tc["type"] = "function"
    func: dict[str, Any] = {}
    if name is not None:
        func["name"] = name
    if arguments is not None:
        func["arguments"] = arguments
    if func:
        tc["function"] = func
    choice: dict[str, Any] = {"index": 0, "delta": {"tool_calls": [tc]}}
    if finish_reason is not None:
        choice["finish_reason"] = finish_reason
        choice["delta"] = {}
    return _sse_json({"choices": [choice]})


def _usage_chunk(usage: dict[str, int], finish_reason: str = "stop") -> bytes:
    return _sse_json(
        {
            "choices": [{"index": 0, "delta": {}, "finish_reason": finish_reason}],
            "usage": usage,
        }
    )


def _done() -> bytes:
    return b"data: [DONE]\n\n"


def _client(base_url: str, **kwargs) -> LLMClient:
    # Loopback must not inherit host HTTP(S)_PROXY / SOCKS settings.
    kwargs.setdefault("trust_env", False)
    return LLMClient(
        base_url=base_url,
        api_key="test-key",
        model="fixture-model",
        timeout_seconds=5.0,
        **kwargs,
    )


class SpyTool(Tool):
    name = "spy_tool"
    description = "spy"
    side_effect = SideEffectClass.NON_IDEMPOTENT
    parameters = {
        "type": "object",
        "properties": {"value": {"type": "string"}},
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
            output=f"ok:{params.get('value')}",
        )


class TrackingTool(Tool):
    """Named spy so fragmented function.name can resolve to distinct tools."""

    description = "tracking"
    side_effect = SideEffectClass.NON_IDEMPOTENT
    parameters = {
        "type": "object",
        "properties": {"value": {"type": "string"}},
        "required": ["value"],
        "additionalProperties": False,
    }

    def __init__(self, tool_name: str) -> None:
        self.name = tool_name
        self.calls: list[dict] = []

    async def execute(self, params: dict, ctx: ToolContext) -> ToolResult:
        self.calls.append({"params": dict(params), "call_id": ctx.call_id})
        return ToolResult(
            call_id=ctx.call_id,
            name=self.name,
            success=True,
            output=f"ok:{params.get('value')}",
        )


class _StreamThenAnswer:
    """Duck-typed LLM for AgentLoop: first call streams via inner, then final answer."""

    def __init__(self, inner: LLMClient, final_text: str = "done"):
        self.inner = inner
        self.final_text = final_text
        self.model = "hybrid"
        self._n = 0
        self._owns = False

    @property
    def owns_http_client(self) -> bool:
        return self._owns

    async def stream_chat(self, messages, tools=None):
        self._n += 1
        if self._n == 1:
            async for e in self.inner.stream_chat(messages, tools):
                yield e
            return
        yield LLMStreamEvent(
            "llm_stream_done",
            {
                "response": LLMResponse(
                    text=self.final_text,
                    tool_calls=[],
                    usage={"total_tokens": 1, "provenance": "provider"},
                    capability=StreamCapability.STREAMING,
                ),
                "finish_reason": "stop",
                "usage": {"total_tokens": 1, "provenance": "provider"},
                "has_tool_calls": False,
                "capability": "streaming",
            },
        )

    async def chat(self, messages, tools=None):
        # Non-stream path unused when use_llm_stream=True
        raise RuntimeError("chat() not used in stream tests")

    async def aclose(self):
        await self.inner.aclose()


# ---------------------------------------------------------------------------
# Parser unit tests (no network)
# ---------------------------------------------------------------------------


class TestSSEAggregator:
    def test_cross_chunk_lines_and_comments(self):
        agg = OpenAIStreamAggregator()
        part1 = b'data: {"choices":[{"delta":{"content":"Hel'
        part2 = b'lo"}}]}\n\n: keep-alive\n\n'
        assert agg.feed_bytes(part1) == []
        obs = agg.feed_bytes(part2)
        assert obs[0]["event"] == "message_delta"
        assert obs[0]["text"] == "Hello"
        result = agg.finish()
        assert result.fail is not None
        assert result.fail.kind == StreamFailKind.INCOMPLETE

    def test_interleaved_tool_indices(self):
        agg = OpenAIStreamAggregator()
        frames = [
            _tool_chunk(index=0, call_id="c0", name="write_file", arguments='{"path":'),
            _tool_chunk(index=1, call_id="c1", name="read_file", arguments='{"path":'),
            _tool_chunk(index=0, arguments='"a.txt","content":"x"}'),
            _tool_chunk(index=1, arguments='"a.txt"}'),
            _usage_chunk(
                {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3},
                "tool_calls",
            ),
            _done(),
        ]
        for frame in frames:
            agg.feed_bytes(frame)
        result = agg.finish()
        assert result.fail is None
        assert len(result.tool_calls) == 2
        assert result.tool_calls[0]["id"] == "c0"
        assert result.tool_calls[0]["arguments"] == {"path": "a.txt", "content": "x"}
        assert result.tool_calls[1]["arguments"] == {"path": "a.txt"}

    def test_interleaved_id_name_arguments_fragments_concat(self):
        """Reproduce overwrite bug: id/name must concat like arguments, by index."""
        agg = OpenAIStreamAggregator()
        frames = [
            # index 0: id "call_" + "123", name "write_" + "file", args split
            _tool_chunk(index=0, call_id="call_", name="write_", arguments='{"path":'),
            # index 1 interleaved: id "call_" + "456", name "read_" + "file"
            _tool_chunk(index=1, call_id="call_", name="read_", arguments='{"path":'),
            _tool_chunk(index=0, call_id="123", name="file", arguments='"a.txt","content":"x"}'),
            _tool_chunk(index=1, call_id="456", name="file", arguments='"a.txt"}'),
            _usage_chunk(
                {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3},
                "tool_calls",
            ),
            _done(),
        ]
        for frame in frames:
            agg.feed_bytes(frame)
        result = agg.finish()
        assert result.fail is None
        assert len(result.tool_calls) == 2
        assert result.tool_calls[0]["id"] == "call_123"
        assert result.tool_calls[0]["name"] == "write_file"
        assert result.tool_calls[0]["arguments"] == {"path": "a.txt", "content": "x"}
        assert result.tool_calls[0]["parse_error"] is None
        assert result.tool_calls[1]["id"] == "call_456"
        assert result.tool_calls[1]["name"] == "read_file"
        assert result.tool_calls[1]["arguments"] == {"path": "a.txt"}
        assert result.tool_calls[1]["parse_error"] is None

    def test_eof_without_termination_is_incomplete(self):
        agg = OpenAIStreamAggregator()
        agg.feed_bytes(_content_chunk("hi"))
        result = agg.finish()
        assert result.fail is not None
        assert result.fail.kind == StreamFailKind.INCOMPLETE


# ---------------------------------------------------------------------------
# Loopback HTTP transport tests
# ---------------------------------------------------------------------------


class TestLoopbackStreaming:
    @pytest.mark.asyncio
    async def test_first_chunk_observed_before_rest_released(self, sse_server):
        base_url, configure, scenario = sse_server
        configure(
            [
                _content_chunk("FIRST"),
                _content_chunk("SECOND"),
                _usage_chunk({"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}),
                _done(),
            ],
            gate_after_first_data=True,
        )
        client = _client(base_url)
        got_first = asyncio.Event()
        texts: list[str] = []

        async def consume():
            async for event in client.stream_chat([{"role": "user", "content": "hi"}]):
                if event.event == "message_delta":
                    texts.append(event.data["text"])
                    if event.data["text"] == "FIRST" and not got_first.is_set():
                        got_first.set()
                if event.event == "llm_stream_done":
                    return event.data["response"]
            return None

        task = asyncio.create_task(consume())
        await asyncio.wait_for(got_first.wait(), timeout=5)
        assert not scenario.release_event.is_set()
        assert scenario.first_data_sent.is_set()
        assert texts == ["FIRST"]
        scenario.release_event.set()
        response = await asyncio.wait_for(task, timeout=5)
        assert response is not None
        assert response.text == "FIRSTSECOND"
        assert response.first_chunk_monotonic is not None
        assert response.complete_monotonic is not None
        assert response.complete_monotonic >= response.first_chunk_monotonic
        assert response.usage["provenance"] == "provider"
        await client.aclose()

    @pytest.mark.asyncio
    async def test_text_deltas_concat_and_usage_preserved(self, sse_server):
        base_url, configure, _ = sse_server
        configure(
            [
                _content_chunk("A"),
                _content_chunk("B"),
                _content_chunk("C"),
                _usage_chunk({"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}),
                _done(),
            ]
        )
        client = _client(base_url)
        events = [e async for e in client.stream_chat([{"role": "user", "content": "x"}])]
        done = events[-1]
        assert done.event == "llm_stream_done"
        resp: LLMResponse = done.data["response"]
        assert resp.text == "ABC"
        assert resp.usage["total_tokens"] == 15
        assert resp.capability == StreamCapability.STREAMING
        await client.aclose()

    @pytest.mark.asyncio
    async def test_interleaved_tools_execute_once_each(self, sse_server, tmp_path):
        base_url, configure, _ = sse_server
        configure(
            [
                _tool_chunk(
                    index=0, call_id="w1", name="write_file", arguments='{"path":"o.txt","con'
                ),
                _tool_chunk(index=1, call_id="r1", name="read_file", arguments='{"path":'),
                _tool_chunk(index=0, arguments='tent":"hello"}'),
                _tool_chunk(index=1, arguments='"o.txt"}'),
                _usage_chunk(
                    {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                    finish_reason="tool_calls",
                ),
                _done(),
            ]
        )
        hybrid = _StreamThenAnswer(_client(base_url), final_text="done")
        tools = ToolRegistry()
        tools.register(WriteFileTool())
        tools.register(ReadFileTool())
        agent = AgentLoop(
            llm=hybrid,  # type: ignore[arg-type]
            tools=tools,
            sandbox=Sandbox(workspace_root=tmp_path),
            budget=Budget(max_steps=5, total_timeout_seconds=30, step_timeout_seconds=10),
            enabled_tools=["write_file", "read_file"],
            use_llm_stream=True,
        )
        result = await agent.run("write and read", task_id="hp02-interleave")
        assert result.success is True
        assert result.total_tool_invocations == 2
        assert (tmp_path / "o.txt").read_text(encoding="utf-8") == "hello"
        await hybrid.aclose()

    @pytest.mark.asyncio
    async def test_interleaved_id_name_arg_fragments_execute_once_each(
        self, sse_server, tmp_path
    ):
        """AgentLoop: two indices, id/name/arguments all cross-frame; each tool once."""
        base_url, configure, _ = sse_server
        configure(
            [
                _tool_chunk(
                    index=0, call_id="call_", name="write_", arguments='{"value":"'
                ),
                _tool_chunk(
                    index=1, call_id="call_", name="read_", arguments='{"value":"'
                ),
                _tool_chunk(index=0, call_id="123", name="file", arguments='alpha"}'),
                _tool_chunk(index=1, call_id="456", name="file", arguments='beta"}'),
                _usage_chunk(
                    {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                    finish_reason="tool_calls",
                ),
                _done(),
            ]
        )
        write_spy = TrackingTool("write_file")
        read_spy = TrackingTool("read_file")
        hybrid = _StreamThenAnswer(_client(base_url), final_text="done")
        tools = ToolRegistry()
        tools.register(write_spy)
        tools.register(read_spy)
        agent = AgentLoop(
            llm=hybrid,  # type: ignore[arg-type]
            tools=tools,
            sandbox=Sandbox(workspace_root=tmp_path),
            budget=Budget(max_steps=5, total_timeout_seconds=30, step_timeout_seconds=10),
            enabled_tools=["write_file", "read_file"],
            use_llm_stream=True,
        )
        result = await agent.run("fragmented id/name", task_id="hp02-id-name-frag")
        assert result.success is True
        assert result.total_tool_invocations == 2
        assert len(write_spy.calls) == 1
        assert len(read_spy.calls) == 1
        assert write_spy.calls[0]["call_id"] == "call_123"
        assert write_spy.calls[0]["params"] == {"value": "alpha"}
        assert read_spy.calls[0]["call_id"] == "call_456"
        assert read_spy.calls[0]["params"] == {"value": "beta"}
        await hybrid.aclose()

    @pytest.mark.asyncio
    async def test_interleaved_id_name_arg_fragments_file_tools_call_ids(
        self, sse_server, tmp_path
    ):
        """Second AgentLoop case: fragmented id/name resolve to real file tools."""
        base_url, configure, _ = sse_server
        configure(
            [
                _tool_chunk(
                    index=0,
                    call_id="call_",
                    name="write_",
                    arguments='{"path":"frag.txt","con',
                ),
                _tool_chunk(
                    index=1, call_id="call_", name="read_", arguments='{"path":'
                ),
                _tool_chunk(index=0, call_id="w99", name="file", arguments='tent":"z"}'),
                _tool_chunk(index=1, call_id="r99", name="file", arguments='"frag.txt"}'),
                _usage_chunk(
                    {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                    finish_reason="tool_calls",
                ),
                _done(),
            ]
        )
        seen: list[tuple[str, str]] = []
        write_tool = WriteFileTool()
        read_tool = ReadFileTool()
        _write_exec = write_tool.execute
        _read_exec = read_tool.execute

        async def wrap_write(params, ctx):
            seen.append(("write_file", ctx.call_id))
            return await _write_exec(params, ctx)

        async def wrap_read(params, ctx):
            seen.append(("read_file", ctx.call_id))
            return await _read_exec(params, ctx)

        write_tool.execute = wrap_write  # type: ignore[method-assign]
        read_tool.execute = wrap_read  # type: ignore[method-assign]

        hybrid = _StreamThenAnswer(_client(base_url), final_text="done")
        tools = ToolRegistry()
        tools.register(write_tool)
        tools.register(read_tool)
        agent = AgentLoop(
            llm=hybrid,  # type: ignore[arg-type]
            tools=tools,
            sandbox=Sandbox(workspace_root=tmp_path),
            budget=Budget(max_steps=5, total_timeout_seconds=30, step_timeout_seconds=10),
            enabled_tools=["write_file", "read_file"],
            use_llm_stream=True,
        )
        result = await agent.run("file tools fragmented", task_id="hp02-id-name-files")
        assert result.success is True
        assert result.total_tool_invocations == 2
        assert (tmp_path / "frag.txt").read_text(encoding="utf-8") == "z"
        assert seen == [("write_file", "call_w99"), ("read_file", "call_r99")]
        await hybrid.aclose()

    @pytest.mark.asyncio
    async def test_incomplete_stream_executes_zero_tools(self, sse_server, tmp_path):
        base_url, configure, _ = sse_server
        configure([], fail_mode="drop")
        spy = SpyTool()
        tools = ToolRegistry()
        tools.register(spy)
        client = _client(base_url)
        agent = AgentLoop(
            llm=client,
            tools=tools,
            sandbox=Sandbox(workspace_root=tmp_path),
            budget=Budget(max_steps=3, total_timeout_seconds=20, step_timeout_seconds=10),
            enabled_tools=["spy_tool"],
            use_llm_stream=True,
            retry_config=RetryConfig(max_retries=0, retry_on=["http", "network", "timeout"]),
        )
        result = await agent.run("should fail incomplete", task_id="hp02-incomplete")
        assert result.success is False
        assert len(spy.calls) == 0
        assert result.total_tool_invocations == 0
        await client.aclose()

    @pytest.mark.asyncio
    async def test_oversized_args_zero_tools(self, sse_server, tmp_path):
        base_url, configure, _ = sse_server
        huge = "x" * (DEFAULT_MAX_ARGUMENT_BYTES + 10)
        configure(
            [
                _tool_chunk(
                    index=0,
                    call_id="big",
                    name="spy_tool",
                    arguments='{"value":"' + huge + '"}',
                ),
                _usage_chunk({"total_tokens": 1}, "tool_calls"),
                _done(),
            ]
        )
        spy = SpyTool()
        tools = ToolRegistry()
        tools.register(spy)
        client = _client(base_url, max_tool_argument_bytes=DEFAULT_MAX_ARGUMENT_BYTES)
        agent = AgentLoop(
            llm=client,
            tools=tools,
            sandbox=Sandbox(workspace_root=tmp_path),
            budget=Budget(max_steps=3, total_timeout_seconds=20, step_timeout_seconds=10),
            enabled_tools=["spy_tool"],
            use_llm_stream=True,
            retry_config=RetryConfig(max_retries=0),
        )
        result = await agent.run("oversized", task_id="hp02-big")
        assert len(spy.calls) == 0
        assert result.total_tool_invocations == 0
        await client.aclose()

    @pytest.mark.asyncio
    async def test_invalid_json_tool_args_still_complete_stream_but_hp01_blocks(
        self, sse_server, tmp_path
    ):
        base_url, configure, _ = sse_server
        configure(
            [
                _tool_chunk(
                    index=0,
                    call_id="bad",
                    name="spy_tool",
                    arguments='{"value":',
                ),
                _usage_chunk({"total_tokens": 1}, "tool_calls"),
                _done(),
            ]
        )
        spy = SpyTool()
        tools = ToolRegistry()
        tools.register(spy)
        client = _StreamThenAnswer(_client(base_url), final_text="recovered")
        agent = AgentLoop(
            llm=client,  # type: ignore[arg-type]
            tools=tools,
            sandbox=Sandbox(workspace_root=tmp_path),
            budget=Budget(max_steps=5, total_timeout_seconds=20, step_timeout_seconds=10),
            enabled_tools=["spy_tool"],
            use_llm_stream=True,
        )
        result = await agent.run("bad json args", task_id="hp02-badjson")
        assert len(spy.calls) == 0
        assert result.total_tool_invocations == 0
        assert result.success is True
        await client.aclose()

    @pytest.mark.asyncio
    async def test_cancel_closes_active_stream_response(self, sse_server):
        base_url, configure, scenario = sse_server
        configure(
            [
                _content_chunk("slow"),
                _content_chunk("tail"),
                _done(),
            ],
            gate_after_first_data=True,
        )
        client = _client(base_url)
        got_first = asyncio.Event()

        async def consume() -> None:
            agen = client.stream_chat([{"role": "user", "content": "x"}])
            try:
                async for event in agen:
                    if event.event == "message_delta" and not got_first.is_set():
                        got_first.set()
                    # Keep consuming until cancelled.
            finally:
                await agen.aclose()

        task = asyncio.create_task(consume())
        await asyncio.wait_for(got_first.wait(), timeout=CLEANUP_TIMEOUT_S)
        assert scenario.first_data_sent.is_set()
        assert client._active_response is not None

        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        assert client._active_response is None
        # Unblock server if still gated; handler must finish in bounded time.
        scenario.release_event.set()
        await asyncio.wait_for(scenario.handler_done.wait(), timeout=CLEANUP_TIMEOUT_S)

        # Owned client can still be used after cancel, then closed.
        configure(
            [
                _content_chunk("after-cancel"),
                _usage_chunk({"total_tokens": 1}),
                _done(),
            ]
        )
        events = [e async for e in client.stream_chat([{"role": "user", "content": "y"}])]
        assert events[-1].event == "llm_stream_done"
        assert events[-1].data["response"].text == "after-cancel"
        assert client.owns_http_client is True
        await client.aclose()
        assert client.http_client is None

    @pytest.mark.asyncio
    async def test_agentloop_cancel_during_stream_stall_no_writes(self, sse_server, tmp_path):
        """AgentLoop + loopback: cancel while stream gated after first frame; no write tools."""
        base_url, configure, scenario = sse_server
        configure(
            [
                _tool_chunk(
                    index=0,
                    call_id="w1",
                    name="write_file",
                    arguments='{"path":"x.txt","content":"nope"}',
                ),
                _usage_chunk({"total_tokens": 1}, "tool_calls"),
                _done(),
            ],
            gate_after_first_data=True,
        )
        cancel = asyncio.Event()
        write = WriteFileTool()
        calls = {"n": 0}
        _orig = write.execute

        async def counting_exec(params, ctx):
            calls["n"] += 1
            return await _orig(params, ctx)

        write.execute = counting_exec  # type: ignore[method-assign]
        tools = ToolRegistry()
        tools.register(write)
        client = _client(base_url)
        agent = AgentLoop(
            llm=client,
            tools=tools,
            sandbox=Sandbox(workspace_root=tmp_path),
            budget=Budget(max_steps=3, total_timeout_seconds=30, step_timeout_seconds=20),
            enabled_tools=["write_file"],
            use_llm_stream=True,
            cancel_event=cancel,
            retry_config=RetryConfig(max_retries=0),
        )

        async def run_and_cancel():
            return await agent.run("stream stall cancel", task_id="stall-cancel")

        task = asyncio.create_task(run_and_cancel())
        await asyncio.wait_for(scenario.first_data_sent.wait(), timeout=CLEANUP_TIMEOUT_S)
        cancel.set()
        # Release gate so server can finish; agent should already be stopping.
        scenario.release_event.set()
        result = await asyncio.wait_for(task, timeout=CLEANUP_TIMEOUT_S + 5)
        assert result.success is False
        assert result.failure_reason in (
            FailureReason.USER_CANCELLED,
            FailureReason.CANCELLED,
        )
        assert calls["n"] == 0
        assert not (tmp_path / "x.txt").exists()
        await client.aclose()

    @pytest.mark.asyncio
    async def test_cancel_does_not_close_borrowed_client(self, sse_server):
        base_url, configure, scenario = sse_server
        configure(
            [
                _content_chunk("slow"),
                _content_chunk("tail"),
                _done(),
            ],
            gate_after_first_data=True,
        )
        shared = httpx.AsyncClient(timeout=5.0, trust_env=False)
        client = _client(base_url, http_client=shared, owns_http_client=False)
        got_first = asyncio.Event()

        async def consume() -> None:
            agen = client.stream_chat([{"role": "user", "content": "x"}])
            try:
                async for event in agen:
                    if event.event == "message_delta" and not got_first.is_set():
                        got_first.set()
            finally:
                await agen.aclose()

        task = asyncio.create_task(consume())
        await asyncio.wait_for(got_first.wait(), timeout=CLEANUP_TIMEOUT_S)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        assert client._active_response is None
        scenario.release_event.set()
        await asyncio.wait_for(scenario.handler_done.wait(), timeout=CLEANUP_TIMEOUT_S)

        await client.aclose()
        assert not shared.is_closed
        # Borrowed client remains usable for another request.
        configure(
            [
                _content_chunk("borrowed-ok"),
                _usage_chunk({"total_tokens": 1}),
                _done(),
            ]
        )
        client2 = _client(base_url, http_client=shared, owns_http_client=False)
        events = [e async for e in client2.stream_chat([{"role": "user", "content": "z"}])]
        assert events[-1].data["response"].text == "borrowed-ok"
        await client2.aclose()
        assert not shared.is_closed
        await shared.aclose()

    @pytest.mark.asyncio
    async def test_client_reuse_across_requests_then_aclose(self, sse_server):
        base_url, configure, scenario = sse_server
        configure(
            [
                _content_chunk("one"),
                _usage_chunk({"total_tokens": 1}),
                _done(),
            ]
        )
        client = _client(base_url)
        async with client:
            http1 = client.http_client
            assert http1 is not None
            events1 = [e async for e in client.stream_chat([{"role": "user", "content": "1"}])]
            assert events1[-1].event == "llm_stream_done"
            configure(
                [
                    _content_chunk("two"),
                    _usage_chunk({"total_tokens": 2}),
                    _done(),
                ],
                reset_count=False,
            )
            events2 = [e async for e in client.stream_chat([{"role": "user", "content": "2"}])]
            assert events2[-1].event == "llm_stream_done"
            assert client.http_client is http1
            assert scenario.request_count == 2
        assert client.http_client is None

    @pytest.mark.asyncio
    async def test_borrowed_client_not_closed(self, sse_server):
        base_url, configure, _ = sse_server
        configure([_content_chunk("x"), _usage_chunk({"total_tokens": 1}), _done()])
        shared = httpx.AsyncClient(timeout=5.0, trust_env=False)
        client = _client(base_url, http_client=shared, owns_http_client=False)
        assert client.owns_http_client is False
        _ = [e async for e in client.stream_chat([{"role": "user", "content": "x"}])]
        await client.aclose()
        # Borrowed client still open — probe with a connection attempt.
        assert not shared.is_closed
        await shared.aclose()

    @pytest.mark.asyncio
    async def test_non_streaming_capability_no_fake_ttft(self):
        class JsonHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):  # noqa: A003
                return

            def do_POST(self):  # noqa: N802
                length = int(self.headers.get("Content-Length", "0"))
                self.rfile.read(length)
                body = {
                    "choices": [
                        {
                            "message": {"content": "hello", "tool_calls": []},
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                }
                raw = json.dumps(body).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

        import threading

        server = ThreadingHTTPServer(("127.0.0.1", 0), JsonHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address
        try:
            client = _client(f"http://127.0.0.1:{port}/v1", supports_streaming=False)
            assert client.capability == StreamCapability.NON_STREAMING
            events = [e async for e in client.stream_chat([{"role": "user", "content": "hi"}])]
            assert len(events) == 1
            assert events[0].event == "llm_stream_done"
            assert events[0].data["capability"] == "non_streaming"
            assert events[0].data["first_chunk_monotonic"] is None
            resp = events[0].data["response"]
            assert resp.text == "hello"
            assert resp.first_chunk_monotonic is None
            await client.aclose()
        finally:
            server.shutdown()
            thread.join(timeout=5)

    @pytest.mark.asyncio
    async def test_missing_usage_is_unknown_not_zero(self, sse_server):
        base_url, configure, _ = sse_server
        configure(
            [
                _content_chunk("hi"),
                _sse_json({"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}),
                _done(),
            ]
        )
        client = _client(base_url)
        events = [e async for e in client.stream_chat([{"role": "user", "content": "x"}])]
        resp = events[-1].data["response"]
        assert resp.usage["provenance"] == "unknown"
        assert resp.usage["total_tokens"] is None
        assert resp.usage["prompt_tokens"] is None
        await client.aclose()

    @pytest.mark.asyncio
    async def test_http_400_not_retried(self, sse_server):
        base_url, configure, scenario = sse_server
        configure([], fail_mode="400")
        client = _client(base_url)
        policy = RetryPolicy(RetryConfig(max_retries=3, retry_on=["http", "timeout", "network"]))
        with pytest.raises(LLMError) as exc:
            await policy.execute(client.chat, [{"role": "user", "content": "x"}])
        assert exc.value.status_code == 400
        assert scenario.request_count == 1
        assert len(policy.sink.attempts) == 1
        assert policy.sink.attempts[0].success is False
        await client.aclose()

    @pytest.mark.asyncio
    async def test_http_429_retried_then_success(self, sse_server):
        base_url, configure, scenario = sse_server
        configure(
            [
                _content_chunk("ok"),
                _usage_chunk({"total_tokens": 3}),
                _done(),
            ],
            fail_mode="429_then_ok",
        )
        client = _client(base_url)
        policy = RetryPolicy(
            RetryConfig(
                max_retries=2,
                backoff_base_seconds=0.01,
                backoff_factor=1.0,
                retry_on=["http", "timeout", "network"],
            )
        )

        async def stream_once():
            final = None
            async for event in client.stream_chat([{"role": "user", "content": "x"}]):
                if event.event == "llm_error":
                    raise LLMError(
                        event.data["message"],
                        kind=LLMErrorKind(event.data["kind"]),
                        status_code=event.data.get("status_code"),
                    )
                if event.event == "llm_stream_done":
                    final = event.data["response"]
            return final

        resp = await policy.execute(stream_once)
        assert resp.text == "ok"
        assert scenario.request_count == 2
        assert len(policy.sink.attempts) == 2
        assert policy.sink.attempts[0].success is False
        assert policy.sink.attempts[0].status_code == 429
        assert policy.sink.attempts[1].success is True
        await client.aclose()

    @pytest.mark.asyncio
    async def test_parse_error_not_retried(self):
        policy = RetryPolicy(RetryConfig(max_retries=3, retry_on=["http", "parse", "timeout"]))
        calls = {"n": 0}

        async def boom():
            calls["n"] += 1
            raise LLMError("bad", kind=LLMErrorKind.PARSE)

        with pytest.raises(LLMError):
            await policy.execute(boom)
        assert calls["n"] == 1


class TestNormalizeUsage:
    def test_absent_usage_unknown(self):
        u = normalize_usage(None)
        assert u["provenance"] == "unknown"
        assert u["total_tokens"] is None

    def test_provider_usage(self):
        u = normalize_usage({"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3})
        assert u["provenance"] == "provider"
        assert u["total_tokens"] == 3


class TestNonStreamParseUsage:
    def test_parse_response_missing_usage_not_zero(self):
        client = LLMClient(base_url="https://unused.invalid/v1", api_key="k", model="m")
        resp = client._parse_response(
            {
                "choices": [
                    {
                        "message": {"content": "hi", "tool_calls": []},
                        "finish_reason": "stop",
                    }
                ]
            }
        )
        assert resp.usage["provenance"] == "unknown"
        assert resp.usage["total_tokens"] is None
