"""Structured schemas for LLM patch planning."""

from __future__ import annotations

from pydantic import BaseModel, Field


class FileEdit(BaseModel):
    """One full-file rewrite proposed by the LLM."""

    path: str
    content: str
    reason: str = ""


class PatchPlan(BaseModel):
    """JSON patch plan returned by the LLM developer."""

    summary: str
    edits: list[FileEdit] = Field(default_factory=list)
    confidence: float = 0.0
    needs_more_context: bool = False
    requested_context: list[str] = Field(default_factory=list)
