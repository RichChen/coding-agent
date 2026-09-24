"""OpenAI-compatible chat completions client for DeepSeek and similar providers."""

from __future__ import annotations

import http.client
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol


class MissingLLMConfigError(RuntimeError):
    """Raised when required LLM environment variables are absent."""


@dataclass(frozen=True)
class LLMConfig:
    """Runtime LLM configuration loaded from environment variables."""

    provider: str
    model: str
    base_url: str
    api_key: str
    timeout_seconds: int = 60
    max_tokens: int = 4096

    @classmethod
    def from_env(cls, *, require_key: bool = True) -> LLMConfig:
        api_key = os.environ.get("LLM_API_KEY", "").strip()
        if require_key and not api_key:
            raise MissingLLMConfigError(
                "LLM_API_KEY is not set. Export it in your shell or use --mock-llm."
            )
        base_url = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com").rstrip("/")
        if base_url.endswith("/v1"):
            pass
        elif not base_url.endswith("/v1"):
            base_url = f"{base_url}/v1"
        return cls(
            provider=os.environ.get("LLM_PROVIDER", "deepseek"),
            model=os.environ.get("LLM_MODEL", "deepseek-v4-pro"),
            base_url=base_url,
            api_key=api_key,
            timeout_seconds=int(os.environ.get("LLM_TIMEOUT_SECONDS", "60")),
            max_tokens=int(os.environ.get("LLM_MAX_TOKENS", "4096")),
        )


class ModelClientProtocol(Protocol):
    """Protocol for LLM clients used by LLMDeveloperAgent."""

    def complete_json(
        self,
        *,
        system: str,
        user: str,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> dict[str, Any]:
        ...


@dataclass
class ModelClient:
    """HTTP client for OpenAI-compatible Chat Completions JSON responses."""

    config: LLMConfig

    def complete_json(
        self,
        *,
        system: str,
        user: str,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        effective_max_tokens = max_tokens if max_tokens is not None else self.config.max_tokens
        url = f"{self.config.base_url}/chat/completions"
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": effective_max_tokens,
            "response_format": {"type": "json_object"},
        }
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=self.config.timeout_seconds,
            ) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            return {
                "error_type": "http_error",
                "status_code": exc.code,
                "message": detail,
                "llm_wall_time_ms": (time.perf_counter() - started) * 1000,
            }
        except urllib.error.URLError as exc:
            return {
                "error_type": "network_error",
                "message": str(exc.reason),
                "llm_wall_time_ms": (time.perf_counter() - started) * 1000,
            }
        except (http.client.IncompleteRead, TimeoutError, OSError) as exc:
            return {
                "error_type": "network_error",
                "message": str(exc),
                "llm_wall_time_ms": (time.perf_counter() - started) * 1000,
            }

        parsed = json.loads(raw)
        content = (
            parsed.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        usage = parsed.get("usage", {})
        prompt_tokens = int(usage.get("prompt_tokens", 0))
        completion_tokens = int(usage.get("completion_tokens", 0))
        token_estimate_mode = "provider_usage" if usage else "char_approx"
        if not usage:
            prompt_tokens = max(1, len(system) // 4 + len(user) // 4)
            completion_tokens = max(1, len(content) // 4)

        try:
            data = json.loads(content) if isinstance(content, str) else content
        except json.JSONDecodeError as exc:
            return {
                "error_type": "llm_parse_error",
                "message": str(exc),
                "raw_content_preview": str(content)[:200],
                "llm_wall_time_ms": (time.perf_counter() - started) * 1000,
                "llm_prompt_tokens_estimate": prompt_tokens,
                "llm_completion_tokens_estimate": completion_tokens,
                "token_estimate_mode": token_estimate_mode,
            }

        if not isinstance(data, dict):
            return {
                "error_type": "llm_parse_error",
                "message": "LLM response JSON is not an object",
                "llm_wall_time_ms": (time.perf_counter() - started) * 1000,
                "llm_prompt_tokens_estimate": prompt_tokens,
                "llm_completion_tokens_estimate": completion_tokens,
                "token_estimate_mode": token_estimate_mode,
            }

        data["llm_wall_time_ms"] = (time.perf_counter() - started) * 1000
        data["llm_prompt_tokens_estimate"] = prompt_tokens
        data["llm_completion_tokens_estimate"] = completion_tokens
        data["token_estimate_mode"] = token_estimate_mode
        return data


@dataclass
class MockModelClient:
    """Deterministic LLM client for unit tests and offline ablation."""

    responses: list[dict[str, Any]]
    calls: list[dict[str, Any]]

    def __init__(self, responses: list[dict[str, Any]] | None = None) -> None:
        self.responses = list(responses or [])
        self.calls: list[dict[str, Any]] = []

    def complete_json(
        self,
        *,
        system: str,
        user: str,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "system_len": len(system),
                "user_len": len(user),
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )
        if not self.responses:
            return {
                "error_type": "mock_empty",
                "message": "MockModelClient has no queued responses",
                "llm_wall_time_ms": 1.0,
                "llm_prompt_tokens_estimate": len(user) // 4,
                "llm_completion_tokens_estimate": 10,
                "token_estimate_mode": "char_approx",
            }
        response = self.responses.pop(0)
        enriched = dict(response)
        enriched.setdefault("llm_wall_time_ms", 1.0)
        enriched.setdefault("llm_prompt_tokens_estimate", len(user) // 4)
        enriched.setdefault("llm_completion_tokens_estimate", 50)
        enriched.setdefault("token_estimate_mode", "char_approx")
        return enriched
