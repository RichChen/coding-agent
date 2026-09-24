"""Tests for LLM ModelClient."""

from __future__ import annotations

import json

import pytest

from reposkill_agent.llm.client import (
    LLMConfig,
    MissingLLMConfigError,
    MockModelClient,
    ModelClient,
)


def test_mock_model_client_returns_json(monkeypatch):
    client = MockModelClient(
        responses=[
            {
                "summary": "fix",
                "edits": [],
                "confidence": 1.0,
                "needs_more_context": False,
            }
        ]
    )
    result = client.complete_json(system="sys", user="usr")
    assert result["summary"] == "fix"
    assert len(client.calls) == 1


def test_mock_model_client_reports_parse_error_shape():
    client = MockModelClient(responses=[])
    result = client.complete_json(system="sys", user="usr")
    assert result["error_type"] == "mock_empty"


def test_llm_config_requires_api_key(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    with pytest.raises(MissingLLMConfigError):
        LLMConfig.from_env(require_key=True)


def test_llm_config_reads_env(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODEL", "deepseek-v4-pro")
    monkeypatch.setenv("LLM_BASE_URL", "https://api.deepseek.com")
    config = LLMConfig.from_env()
    assert config.api_key == "test-key"
    assert config.model == "deepseek-v4-pro"
    assert config.base_url.endswith("/v1")


def test_model_client_parses_invalid_json(monkeypatch):
    class FakeResponse:
        def read(self):
            payload = {
                "choices": [{"message": {"content": "not-json"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 2},
            }
            return json.dumps(payload).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: FakeResponse())
    config = LLMConfig(
        provider="deepseek",
        model="deepseek-v4-pro",
        base_url="https://api.deepseek.com/v1",
        api_key="test-key",
    )
    client = ModelClient(config)
    result = client.complete_json(system="s", user="u")
    assert result["error_type"] == "llm_parse_error"
