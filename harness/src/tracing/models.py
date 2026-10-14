"""Trace 数据结构：写入 JSONL 的 StepRecord / TraceRun。

English: dataclasses for structured logging.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class StepRecord:
    step: int
    phase: str
    messages_snapshot: int  # 该步时刻 messages 列表长度（用于还原对话膨胀）
    llm_text: str | None = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    elapsed_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        phase_val = self.phase.value if hasattr(self.phase, "value") else self.phase
        return {
            "step": self.step,
            "phase": phase_val,
            "messages_count": self.messages_snapshot,
            "llm_text": self.llm_text,
            "tool_calls": self.tool_calls,
            "tool_results": self.tool_results,
            "elapsed_ms": round(self.elapsed_ms, 2),
        }


@dataclass
class TraceRun:
    task_id: str
    config_name: str
    steps: list[StepRecord] = field(default_factory=list)
    success: bool = False
    final_answer: str | None = None
    failure_reason: str | None = None
    total_elapsed_ms: float = 0.0
    total_tokens: int = 0
    tool_failures: int = 0
    policy_blocks: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
