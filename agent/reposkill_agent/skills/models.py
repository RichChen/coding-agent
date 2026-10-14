"""Skill models and lifecycle stats (SkillCard v2)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SkillSpec(BaseModel):
    """A reusable skill definition (SkillCard v2)."""

    id: str
    name: str
    version: str
    purpose: str
    pattern: str = ""
    required_evidence: list[str] = Field(default_factory=list)
    edit_recipe: list[str] = Field(default_factory=list)
    anti_patterns: list[str] = Field(default_factory=list)
    applies_when: list[str] = Field(default_factory=list)
    not_applicable_when: list[str] = Field(default_factory=list)
    required_context: list[str] = Field(default_factory=list)
    procedure: str = ""
    verifier: str = "manual"
    success_count: int = 0
    failure_count: int = 0
    negative_transfer_notes: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)

    def recipe_lines(self) -> list[str]:
        if self.edit_recipe:
            return self.edit_recipe
        if self.procedure:
            return [line.strip() for line in self.procedure.splitlines() if line.strip()]
        return []

    def evidence_requirements(self) -> list[str]:
        if self.required_evidence:
            return self.required_evidence
        return list(self.required_context)


class SkillEvidenceContext(BaseModel):
    """Signals available for skill evidence gating."""

    issue: str
    tags: list[str] = Field(default_factory=list)
    expected_files: list[str] = Field(default_factory=list)
    test_output: str = ""
    locator_matches: list[str] = Field(default_factory=list)
    repo_files: list[str] = Field(default_factory=list)


class SkillSelection(BaseModel):
    """Selection result from skill retrieval + validation + injection cap."""

    selected: list[SkillSpec] = Field(default_factory=list)
    retrieved_count: int = 0
    validated_count: int = 0
    candidate_count: int = 0
    injected_count: int = 0
    gated_count: int = 0
    rejected: list[dict[str, str]] = Field(default_factory=list)
