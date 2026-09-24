"""Versioned knowledge records. Legacy MemoryHint/JSONL remain unchanged."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import AwareDatetime, Field, model_validator

from reposkill_agent.protocol.public import (
    ArtifactRef,
    Digest,
    StrictModel,
    Versioned,
    canonical,
    digest,
)

MemoryStatus = Literal["candidate", "validated", "stale", "conflicted", "quarantined", "retired"]


def contains_secret(text: str) -> bool:
    """Conservative credential-pattern screening, not a general secret detector."""
    return bool(
        re.search(
            r"(?i)(?:api[_-]?key|password|secret|authorization)\s*[:=]\s*\S+"
            r"|-----BEGIN .*PRIVATE KEY-----|\bsk-[A-Za-z0-9_-]{12,}",
            text,
        )
    )


class BuildUsage(StrictModel):
    method: Literal["rule", "human-authored", "llm"]
    model: str | None = None
    calls: int = Field(default=0, ge=0)
    token_status: Literal["none", "provider", "estimated", "unknown"] = "none"
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    cost: float | None = Field(default=None, ge=0)
    currency: str | None = None
    wall_ms: float = Field(default=0, ge=0)

    @model_validator(mode="after")
    def consistent(self):
        if self.method == "llm":
            if not self.model or self.calls < 1 or self.token_status == "none":
                raise ValueError("missing_builder_usage")
        elif self.calls or self.model or self.token_status != "none":
            raise ValueError("invalid_rule_usage")
        if self.cost is not None and not self.currency:
            raise ValueError("missing_currency")
        return self


class SourceRef(StrictModel):
    task_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    repo_id: str = Field(min_length=1)
    repo_revision: str = Field(min_length=1)
    protocol_mode: Literal["realistic", "diagnostic_oracle"]
    split: Literal["memory_build", "dev", "heldout"]
    occurred_at: AwareDatetime
    artifact: ArtifactRef
    duplicate_group: str | None = None

    @model_validator(mode="after")
    def owned(self):
        if self.artifact.run_id != self.run_id:
            raise ValueError("source_run_mismatch")
        return self


class Dependency(StrictModel):
    kind: Literal["api_signature", "package", "file_hash"]
    key: str = Field(min_length=1)
    expected: str = Field(min_length=1)
    extractor_version: str = "1"
    evidence_ref: str = Field(min_length=1)


class ValidationEvidence(StrictModel):
    artifact: ArtifactRef
    repo_id: str = Field(min_length=1)
    repo_revision: str = Field(min_length=1)
    checked_at: AwareDatetime
    collected: int = Field(gt=0)
    passed: int = Field(ge=0)
    outcome: Literal["pass", "fail"]

    @model_validator(mode="after")
    def counts(self):
        if self.passed > self.collected or (
            self.outcome == "pass" and self.passed != self.collected
        ):
            raise ValueError("invalid_validation_counts")
        return self


class MemoryRecord(Versioned):
    memory_id: str = Field(min_length=1)
    revision: int = Field(default=1, ge=1)
    supersedes: int | None = Field(default=None, ge=1)
    kind: Literal["episode", "procedure", "repo_profile"]
    status: MemoryStatus = "candidate"
    content_hash: Digest
    procedure: str = Field(min_length=1, max_length=20000)
    applicability: tuple[str, ...] = ()
    verification_recipe: str = Field(min_length=1)
    source_repo_id: str = Field(min_length=1)
    sources: tuple[SourceRef, ...] = ()
    created_at: AwareDatetime
    build_usage: BuildUsage
    dependencies: tuple[Dependency, ...] = ()
    dependency_mapping_complete: bool = False
    validation: tuple[ValidationEvidence, ...] = ()
    last_validated_at: AwareDatetime | None = None
    ttl_seconds: int | None = Field(default=None, gt=0)
    conflict_group: str | None = None
    duplicate_group: str | None = None

    @model_validator(mode="after")
    def integrity(self):
        if self.content_hash != digest(self.procedure):
            raise ValueError("memory_content_hash_mismatch")
        if contains_secret(
            canonical(
                {
                    "procedure": self.procedure,
                    "applicability": self.applicability,
                    "recipe": self.verification_recipe,
                }
            )
        ):
            raise ValueError("secret_content_excluded")
        if (self.revision == 1 and self.supersedes is not None) or (
            self.revision > 1 and self.supersedes != self.revision - 1
        ):
            raise ValueError("invalid_revision_lineage")
        if self.status == "validated":
            if (
                not self.sources
                or not self.validation
                or self.last_validated_at is None
                or any(v.outcome != "pass" for v in self.validation)
            ):
                raise ValueError("missing_public_validation")
            if any(s.protocol_mode != "realistic" for s in self.sources):
                raise ValueError("diagnostic_source_not_validated")
            if any(v.repo_id != self.source_repo_id for v in self.validation):
                raise ValueError("validation_repo_mismatch")
            if self.last_validated_at != max(v.checked_at for v in self.validation):
                raise ValueError("validation_time_mismatch")
            refs = {s.artifact.logical_id for s in self.sources}
            refs.update(v.artifact.logical_id for v in self.validation)
            if any(d.evidence_ref not in refs for d in self.dependencies):
                raise ValueError("dependency_provenance_missing")
        keys = {(d.kind, d.key) for d in self.dependencies}
        if len(keys) != len(self.dependencies):
            raise ValueError("duplicate_dependency")
        return self

    def hint(self) -> dict:
        return {
            "memory_id": self.memory_id,
            "revision": self.revision,
            "content_hash": self.content_hash,
            "procedure": self.procedure,
            "applicability": self.applicability,
            "sources": [s.model_dump(mode="json") for s in self.sources],
        }


class UseRecord(StrictModel):
    use_id: str
    run_id: str
    decision_id: str
    memory_id: str
    revision: int
    stage: Literal["retrieved", "selected", "rejected", "actually_injected", "observed_following"]
    reason: str
    receipt_id: str | None = None
    evidence_refs: tuple[str, ...] = ()
    following: Literal["true", "false", "unknown"] = "unknown"

    @model_validator(mode="after")
    def evidence_required(self):
        if self.stage == "actually_injected" and not self.receipt_id:
            raise ValueError("injection_requires_receipt")
        if self.following != "unknown" and (
            self.stage != "observed_following" or not self.evidence_refs
        ):
            raise ValueError("following_requires_evidence")
        return self


VerificationStatus = Literal[
    "validated_fix", "partial_attempt", "failed_attempt", "unverified"
]


class CardDependency(StrictModel):
    """File touched by a historical attempt, plus symbols worth re-checking."""

    path: str = Field(min_length=1)
    symbols: tuple[str, ...] = ()


class MemoryCard(StrictModel):
    """Structured experience distilled from one public source trajectory.

    This is the card form used by the new retrieval plugin. It lives next to
    ``MemoryRecord`` and reuses the same secret screen. It is not a validated
    ``MemoryRecord``: grader status is carried separately and defaults to
    unverified.
    """

    repo: str = Field(min_length=1)
    version: str = Field(min_length=7)
    source_id: str = Field(min_length=1)
    issue_summary: str = Field(min_length=1)
    relevant_files: tuple[str, ...] = ()
    test_commands: tuple[str, ...] = ()
    env_pitfalls: tuple[str, ...] = ()
    fix_approach: str = Field(min_length=1)
    verification_status: VerificationStatus = "unverified"
    dependencies: tuple[CardDependency, ...] = ()
    distillation: Literal["rule", "llm_distilled"] = "rule"
    observations: tuple[str, ...] = ()
    actions: tuple[str, ...] = ()
    public_verification: str = ""
    failure_notes: tuple[str, ...] = ()

    @model_validator(mode="after")
    def screen(self):
        if contains_secret(
            "\n".join(
                (
                    self.issue_summary,
                    self.fix_approach,
                    " ".join(self.env_pitfalls),
                    " ".join(self.test_commands),
                )
            )
        ):
            raise ValueError("secret_content_excluded")
        return self
