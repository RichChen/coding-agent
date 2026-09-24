import pytest

from src.llm.client import (
    LLMClient,
    LLMError,
    LLMErrorKind,
    LLMResponse,
    OpenAICompatibleAdapter,
    ToolCall,
    normalize_usage,
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
        stream_options={"include_usage": True},
    )

    assert adapter.chat_completions_url == "https://api.example.com/v1/chat/completions"
    assert payload["model"] == "model-a"
    assert payload["stream"] is True
    assert payload["tool_choice"] == "auto"
    assert payload["stream_options"]["include_usage"] is True
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
    assert response.usage["provenance"] == "provider"


def test_parse_response_missing_usage_is_unknown():
    client = LLMClient(base_url="https://api.example.com/v1", api_key="k", model="m")
    response = client._parse_response(
        {
            "choices": [
                {
                    "message": {"content": "hi"},
                    "finish_reason": "stop",
                }
            ]
        }
    )
    assert response.usage == normalize_usage(None)
    assert response.usage["total_tokens"] is None
    assert response.usage["provenance"] == "unknown"


def test_retry_policy_uses_llm_error_kind():
    from src.runtime.retry import RetryConfig, RetryPolicy

    config = RetryConfig(retry_on=["timeout", "model_error"])
    retry = RetryPolicy(config)

    assert retry.should_retry(LLMError("timed out", kind=LLMErrorKind.TIMEOUT)) is True
    assert retry.should_retry(LLMError("bad json", kind=LLMErrorKind.PARSE)) is False
    assert retry.should_retry(LLMError("incomplete", kind=LLMErrorKind.INCOMPLETE)) is False
    assert retry.should_retry(LLMError("server error", kind=LLMErrorKind.HTTP)) is False


def test_retry_policy_http_status_code_filtering():
    from src.runtime.retry import RetryConfig, RetryPolicy

    config = RetryConfig(retry_on=["http"])
    retry = RetryPolicy(config)

    assert retry.should_retry(LLMError("503", kind=LLMErrorKind.HTTP, status_code=503)) is True
    assert retry.should_retry(LLMError("429", kind=LLMErrorKind.HTTP, status_code=429)) is True
    assert retry.should_retry(LLMError("404", kind=LLMErrorKind.HTTP, status_code=404)) is False
    assert retry.should_retry(LLMError("400", kind=LLMErrorKind.HTTP, status_code=400)) is False
