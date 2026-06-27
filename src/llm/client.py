"""LLMClient：对 OpenAI 兼容 `/v1/chat/completions` 的薄封装。

English: thin async HTTP client — `chat()` with messages + optional tools → LLMResponse.

设计要点：
  - v0.1 仅异步 `chat()`，无流式。
  - 接受 messages + 可选 tools schema，返回 LLMResponse。
  - 重试/超时在 runtime 的 RetryPolicy，不在此类。
  - 供应商差异尽量只出现在本文件。
"""

from __future__ import annotations

import enum
import json
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Protocol

import httpx


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    text: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    finish_reason: str = "stop"
    usage: dict[str, int] = field(default_factory=dict)

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


class LLMErrorKind(str, enum.Enum):
    TIMEOUT = "timeout"
    HTTP = "http"
    PARSE = "parse"
    UNKNOWN = "unknown"


class LLMError(Exception):
    """Raised when the LLM API returns an error or times out."""

    def __init__(
        self,
        message: str,
        kind: LLMErrorKind = LLMErrorKind.UNKNOWN,
        status_code: int | None = None,
    ):
        self.kind = kind
        self.status_code = status_code
        super().__init__(message)


@dataclass(frozen=True)
class LLMStreamEvent:
    event: str
    data: dict[str, Any] = field(default_factory=dict)


class BaseLLMClient(Protocol):
    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        ...


@dataclass(frozen=True)
class OpenAICompatibleAdapter:
    """Provider adapter for OpenAI-compatible chat completions."""

    base_url: str

    @property
    def chat_completions_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/chat/completions"

    def build_payload(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        temperature: float,
        max_tokens: int,
        stream: bool = False,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        return payload

    def headers(self, api_key: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }


class LLMClient:
    """异步调用 OpenAI 兼容的 chat completions（URL = base_url + "/chat/completions"）。"""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        timeout_seconds: float = 120.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout_seconds = timeout_seconds
        self.adapter = OpenAICompatibleAdapter(base_url=self.base_url)

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        """发送一轮 chat 请求。

        Args:
            messages: OpenAI 格式的 role/content 列表。
            tools: 可选，OpenAI tools JSON Schema 列表。

        Returns:
            LLMResponse：纯文本和/或 tool_calls。

        Raises:
            LLMError: HTTP 错误、超时或响应体无法解析。
        """
        payload = self.adapter.build_payload(
            model=self.model,
            messages=messages,
            tools=tools,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        payload.pop("stream", None)

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            try:
                resp = await client.post(
                    self.adapter.chat_completions_url,
                    json=payload,
                    headers=self.adapter.headers(self.api_key),
                )
                resp.raise_for_status()
            except httpx.TimeoutException:
                raise LLMError(
                    f"LLM request timed out after {self.timeout_seconds}s",
                    kind=LLMErrorKind.TIMEOUT,
                )
            except httpx.HTTPStatusError as e:
                body = e.response.text[:500] if e.response else "(no body)"
                status_code = e.response.status_code if e.response else None
                raise LLMError(
                    f"LLM API error {status_code}: {body}",
                    kind=LLMErrorKind.HTTP,
                    status_code=status_code,
                )

        return self._parse_response(resp.json())

    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[LLMStreamEvent]:
        """Streaming event skeleton.

        The first implementation keeps the stable non-streaming transport and
        exposes stream-shaped events for tracing/UI integration. A future SSE
        implementation can preserve this event contract.
        """
        try:
            response = await self.chat(messages, tools)
        except LLMError as e:
            yield LLMStreamEvent("llm_error", {"kind": e.kind.value, "message": str(e)})
            return

        if response.text:
            yield LLMStreamEvent("message_delta", {"text": response.text})
        for call in response.tool_calls:
            yield LLMStreamEvent(
                "tool_call_delta",
                {"id": call.id, "name": call.name, "arguments": call.arguments},
            )
        yield LLMStreamEvent(
            "llm_stream_done",
            {
                "finish_reason": response.finish_reason,
                "usage": response.usage,
                "has_tool_calls": response.has_tool_calls,
            },
        )

    def _parse_response(self, data: dict[str, Any]) -> LLMResponse:
        try:
            choice = data["choices"][0]
            message = choice["message"]
        except (KeyError, IndexError, TypeError) as e:
            raise LLMError(f"Unable to parse LLM response: {e}", kind=LLMErrorKind.PARSE)

        text = message.get("content") or None

        tool_calls: list[ToolCall] = []
        raw_tool_calls = message.get("tool_calls") or []
        for tc in raw_tool_calls:
            func = tc["function"]
            try:
                args = json.loads(func["arguments"])
            except json.JSONDecodeError:
                args = {}
            tool_calls.append(
                ToolCall(
                    id=tc["id"],
                    name=func["name"],
                    arguments=args,
                )
            )

        usage = data.get("usage", {})

        return LLMResponse(
            text=text,
            tool_calls=tool_calls,
            finish_reason=choice.get("finish_reason", "stop"),
            usage={
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
        )
