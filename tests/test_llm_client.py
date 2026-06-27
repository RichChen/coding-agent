import pytest

from src.llm.client import (
    LLMClient,
    LLMError,
    LLMErrorKind,
    LLMResponse,
    OpenAICompatibleAdapter,
    ToolCall,
)


def test_openai_compatible_adapter_builds_payload_and_headers():
    adapter = OpenAICompatibleAdapter(base_url="https://api.example.com/v1/")

    payload = adapter.build_payload(
        model="model-a",
        messages=[{"role": "user", "content": "hi"}],
        tools=[{"type": "function", "function": {"name": "read_file"}}],
        temperature=0.1,
        max_tokens=123,
        stream=True,
    )

    assert adapter.chat_completions_url == "https://api.example.com/v1/chat/completions"
    assert payload["model"] == "model-a"
    assert payload["stream"] is True
    assert payload["tool_choice"] == "auto"
    assert adapter.headers("secret")["Authorization"] == "Bearer secret"


def test_parse_response_classifies_bad_shape_as_parse_error():
    client = LLMClient(base_url="https://api.example.com/v1", api_key="k", model="m")

    with pytest.raises(LLMError) as exc:
        client._parse_response({"choices": []})

    assert exc.value.kind == LLMErrorKind.PARSE


def test_parse_response_handles_tool_call_arguments():
    client = LLMClient(base_url="https://api.example.com/v1", api_key="k", model="m")

    response = client._parse_response(
        {
            "choices": [
                {
                    "message": {
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "tc1",
                                "function": {
                                    "name": "read_file",
                                    "arguments": "{\"path\": \"a.txt\"}",
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
            "usage": {"total_tokens": 9},
        }
    )

    assert response.has_tool_calls is True
    assert response.tool_calls[0].arguments == {"path": "a.txt"}
    assert response.usage["total_tokens"] == 9


class _StreamingFakeClient(LLMClient):
    def __init__(self, response=None, error: LLMError | None = None):
        self.response = response or LLMResponse(text="hello", usage={"total_tokens": 1})
        self.error = error

    async def chat(self, messages, tools=None):
        if self.error:
            raise self.error
        return self.response


async def _collect_stream(client):
    return [event async for event in client.stream_chat([{"role": "user", "content": "hi"}])]


def test_stream_chat_emits_event_skeleton():
    client = _StreamingFakeClient(
        LLMResponse(
            text="hello",
            tool_calls=[ToolCall(id="tc1", name="read_file", arguments={"path": "a.txt"})],
            usage={"total_tokens": 2},
        )
    )

    import asyncio
    events = asyncio.run(_collect_stream(client))

    assert [event.event for event in events] == [
        "message_delta",
        "tool_call_delta",
        "llm_stream_done",
    ]
    assert events[-1].data["has_tool_calls"] is True


def test_stream_chat_emits_error_event():
    client = _StreamingFakeClient(
        error=LLMError("boom", kind=LLMErrorKind.HTTP),
    )

    import asyncio
    events = asyncio.run(_collect_stream(client))

    assert len(events) == 1
    assert events[0].event == "llm_error"
    assert events[0].data["kind"] == "http"


def test_retry_policy_uses_llm_error_kind():
    from src.runtime.retry import RetryConfig, RetryPolicy

    config = RetryConfig(retry_on=["timeout", "model_error"])
    retry = RetryPolicy(config)

    assert retry.should_retry(LLMError("timed out", kind=LLMErrorKind.TIMEOUT)) is True
    assert retry.should_retry(LLMError("bad json", kind=LLMErrorKind.PARSE)) is False
    assert retry.should_retry(LLMError("server error", kind=LLMErrorKind.HTTP)) is False


def test_retry_policy_http_status_code_filtering():
    from src.runtime.retry import RetryConfig, RetryPolicy

    config = RetryConfig(retry_on=["http"])
    retry = RetryPolicy(config)

    assert retry.should_retry(LLMError("503", kind=LLMErrorKind.HTTP, status_code=503)) is True
    assert retry.should_retry(LLMError("429", kind=LLMErrorKind.HTTP, status_code=429)) is True
    assert retry.should_retry(LLMError("404", kind=LLMErrorKind.HTTP, status_code=404)) is False
    assert retry.should_retry(LLMError("400", kind=LLMErrorKind.HTTP, status_code=400)) is False
