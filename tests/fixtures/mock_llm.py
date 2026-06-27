"""Mock LLMClient that returns prescribed responses for integration testing.

No real API calls — responses are pre-configured in order.
"""

from __future__ import annotations

from src.llm.client import LLMClient, LLMResponse


class MockLLMClient(LLMClient):
    """Returns preset responses in sequence. Raises RuntimeError if exhausted."""

    def __init__(self, responses: list[LLMResponse] | None = None):
        # Bypass LLMClient.__init__ (no real API config needed)
        self._responses = list(responses) if responses else []
        self._call_count = 0
        self.calls: list[dict] = []
        self.model = "mock-model"

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
        return resp
