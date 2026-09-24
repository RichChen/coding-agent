"""Serializable public evidence and bounded action proposals."""

from typing import Literal

from pydantic import Field, field_validator, model_validator

from reposkill_agent.protocol.public import (
    ArtifactRef,
    StrictModel,
    Versioned,
    digest,
    safe_relative,
)


class Observation(StrictModel):
    observation_id: str
    kind: Literal["file", "search", "public_test"]
    path: str
    start_line: int = Field(default=1, ge=1)
    content: str = Field(max_length=24000)
    repo_revision: str
    artifact: ArtifactRef

    _path = field_validator("path")(safe_relative)

    @model_validator(mode="after")
    def matches_artifact(self):
        if (
            digest(self.content) != self.artifact.sha256
            or len(self.content.encode()) != self.artifact.size_bytes
        ):
            raise ValueError("observation_hash_mismatch")
        return self


class EvidenceState(Versioned):
    repo_revision: str
    observations: tuple[Observation, ...] = ()
    proposed_paths: tuple[str, ...] = ()
    searched_queries: tuple[str, ...] = ()
    hypotheses: tuple[str, ...] = ()
    missing_evidence: tuple[str, ...] = ()
    tool_proposals_spent: int = Field(default=0, ge=0)


class Proposal(StrictModel):
    proposal_id: str
    tool: Literal["read", "search"]
    path: str | None = None
    query: str | None = None
    reason: str
    evidence_refs: tuple[str, ...] = ()


class LocatorDecision(StrictModel):
    status: Literal[
        "needs_observation", "evidence_ready", "insufficient_evidence", "budget_exhausted"
    ]
    state: EvidenceState
    proposals: tuple[Proposal, ...] = ()
    selected_paths: tuple[str, ...] = ()
