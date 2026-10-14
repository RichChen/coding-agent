"""Mock LLMClient that returns prescribed responses for integration testing.

No real API calls — responses are pre-configured in order.
"""

from __future__ import annotations

from typing import Any, AsyncIterator

from src.llm.client import LLMClient, LLMResponse, LLMStreamEvent, StreamCapability


class MockLLMClient(LLMClient):
    """Returns preset responses in sequence. Raises RuntimeError if exhausted."""

    def __init__(self, responses: list[LLMResponse] | None = None):
        # Bypass LLMClient.__init__ (no real API config needed)
        self._responses = list(responses) if responses else []
        self._call_count = 0
        self.calls: list[dict] = []
        self.model = "mock-model"
        self.supports_streaming = False  # honest: mock has no real SSE transport
        self._owns_http_client = False
        self._http = None
        self._closed = False
        self._active_response = None

    @property
    def owns_http_client(self) -> bool:
        return False

    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> LLMResponse:
        self.calls.append({"messages": messages, "tools": tools})
        if self._call_count >= len(self._responses):
            raise RuntimeError(
                f"MockLLMClient exhausted: only {len(self._responses)} responses configured, "
                f"got call #{self._call_count + 1}"
            )
        resp = self._responses[self._call_count]
        self._call_count += 1
        if resp.capability is None:
            resp.capability = StreamCapability.NON_STREAMING
        if not resp.usage:
            resp.usage = {
                "prompt_tokens": None,
                "completion_tokens": None,
                "total_tokens": None,
                "provenance": "unknown",
            }
        elif "provenance" not in resp.usage:
            resp.usage = {**resp.usage, "provenance": "provider"}
        return resp

    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[LLMStreamEvent]:
        """Honest non-streaming mock: one complete response, no fake TTFT deltas."""
        response = await self.chat(messages, tools)
        response.capability = StreamCapability.NON_STREAMING
        response.first_chunk_monotonic = None
        yield LLMStreamEvent(
            "llm_stream_done",
            {
                "finish_reason": response.finish_reason,
                "usage": response.usage,
                "has_tool_calls": response.has_tool_calls,
                "capability": StreamCapability.NON_STREAMING.value,
                "response": response,
                "first_chunk_monotonic": None,
                "complete_monotonic": None,
            },
        )

    async def aclose(self) -> None:
        self._closed = True
