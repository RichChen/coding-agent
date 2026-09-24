"""Rule extraction from an allowlisted public trajectory, with no automatic promotion."""

from __future__ import annotations

import json
import time
from datetime import datetime

from reposkill_agent.memory.records import BuildUsage, Dependency, MemoryRecord, SourceRef
from reposkill_agent.memory.source_manifest import SourcePolicy, validate_build_manifest
from reposkill_agent.protocol.public import StrictModel, digest, reject_oracle


class PublicTrajectory(StrictModel):
    issue_summary: str
    public_evidence: tuple[str, ...]
    actions: tuple[str, ...]
    public_verification: str
    failure_notes: tuple[str, ...] = ()


def build_candidate(
    trajectory_text: str,
    source: SourceRef,
    policy: SourcePolicy,
    *,
    now: datetime,
    dependencies: tuple[Dependency, ...] = (),
    dependency_mapping_complete: bool = False,
) -> MemoryRecord:
    started = time.perf_counter()
    validate_build_manifest(policy)
    if policy.source_reasons(source):
        raise ValueError("trajectory_source_rejected")
    if (
        digest(trajectory_text) != source.artifact.sha256
        or len(trajectory_text.encode()) != source.artifact.size_bytes
    ):
        raise ValueError("trajectory_content_changed")
    raw = json.loads(trajectory_text)
    reject_oracle(raw)
    trajectory = PublicTrajectory.model_validate(raw)
    procedure = "\n".join(
        (
            "Issue: " + trajectory.issue_summary,
            *("Evidence: " + s for s in trajectory.public_evidence),
            *("Action: " + s for s in trajectory.actions),
            *("Prior failure: " + s for s in trajectory.failure_notes),
        )
    )
    return MemoryRecord(
        memory_id="trajectory-" + source.artifact.sha256,
        kind="procedure",
        content_hash=digest(procedure),
        procedure=procedure,
        applicability=(trajectory.issue_summary,),
        verification_recipe=trajectory.public_verification,
        source_repo_id=source.repo_id,
        sources=(source,),
        created_at=now,
        dependencies=dependencies,
        dependency_mapping_complete=dependency_mapping_complete,
        build_usage=BuildUsage(
            method="rule", cost=0, currency="USD", wall_ms=(time.perf_counter() - started) * 1000
        ),
    )
