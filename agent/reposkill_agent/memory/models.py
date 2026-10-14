"""Memory hint models (MemoryHint v2)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

MemoryHintType = Literal["repo_profile", "episodic", "procedural"]


class MemoryHint(BaseModel):
    """Compact, actionable memory hint for LLM context."""

    type: MemoryHintType
    source_task_id: str
    confidence: float
    applies_when: list[str] = Field(default_factory=list)
    likely_files: list[str] = Field(default_factory=list)
    successful_pattern: str = ""
    repo_convention: str = ""
    warning: str = ""

    def to_prompt_dict(self) -> dict[str, object]:
        """Serialize for AgentContext and compact prompt injection."""
        return {
            "type": self.type,
            "source_task_id": self.source_task_id,
            "confidence": self.confidence,
            "applies_when": self.applies_when,
            "likely_files": self.likely_files,
            "successful_pattern": self.successful_pattern,
            "repo_convention": self.repo_convention,
            "warning": self.warning,
        }


class MemorySelection(BaseModel):
    """Result of memory retrieval + gating."""

    injected: list[dict[str, object]] = Field(default_factory=list)
    candidate_count: int = 0
    injected_count: int = 0
    gated_count: int = 0
    source_task_ids: list[str] = Field(default_factory=list)
