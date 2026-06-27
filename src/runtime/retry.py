"""重试策略：对 LLM 调用失败做可配置指数退避。

English: RetryPolicy wraps async callable with backoff; error classification is heuristic.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

from src.llm.client import LLMError, LLMErrorKind

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    max_retries: int = 2
    backoff_base_seconds: float = 1.0
    backoff_factor: float = 2.0
    retry_on: list[str] = field(default_factory=lambda: ["timeout", "model_error"])


class RetryPolicy:
    def __init__(self, config: RetryConfig):
        self.config = config

    def should_retry(self, error: Exception) -> bool:
        """根据异常 kind 或信息粗分类，判断是否属于 retry_on 列表中的可重试类型。"""
        if isinstance(error, LLMError):
            if error.kind == LLMErrorKind.HTTP:
                if "http" not in self.config.retry_on:
                    return False
                code = error.status_code
                if code is None:
                    return True
                if code == 429 or code >= 500:
                    return True
                return False
            return error.kind.value in self.config.retry_on
        error_type = self._classify(error)
        return error_type in self.config.retry_on

    async def execute(self, fn, *args, **kwargs):
        """对异步函数 fn 做有限次重试；用尽后抛出最后一次异常。"""
        last_error = None
        for attempt in range(self.config.max_retries + 1):
            try:
                return await fn(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt == self.config.max_retries or not self.should_retry(e):
                    raise
                delay = self.config.backoff_base_seconds * (
                    self.config.backoff_factor ** attempt
                )
                logger.warning(
                    f"Retry attempt {attempt + 1}/{self.config.max_retries} "
                    f"after error: {e}. Waiting {delay:.1f}s."
                )
                await asyncio.sleep(delay)
        raise last_error  # pragma: no cover

    @staticmethod
    def _classify(error: Exception) -> str:
        msg = str(error).lower()
        if "timeout" in msg or "timed out" in msg:
            return "timeout"
        if "model" in msg or "api" in msg or "parse" in msg:
            return "model_error"
        return "unknown"
