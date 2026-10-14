"""Fail-closed provenance admission against a trusted experiment manifest."""

from pydantic import AwareDatetime

from reposkill_agent.memory.records import MemoryRecord, SourceRef
from reposkill_agent.protocol.public import ArtifactRef, StrictModel


class SourcePolicy(StrictModel):
    allowed_sources: tuple[SourceRef, ...]
    allowed_validation_artifacts: tuple[ArtifactRef, ...] = ()
    target_task_ids: tuple[str, ...]
    excluded_artifact_hashes: tuple[str, ...] = ()
    excluded_duplicate_groups: tuple[str, ...] = ()
    cutoff: AwareDatetime
    allowed_repos: tuple[str, ...] = ()

    def source_reasons(self, source: SourceRef) -> tuple[str, ...]:
        reasons = []
        if source not in self.allowed_sources:
            reasons.append("source_not_allowlisted")
        if source.task_id in self.target_task_ids:
            reasons.append("target_source")
        if source.protocol_mode != "realistic":
            reasons.append("diagnostic_source")
        if source.split != "memory_build":
            reasons.append("source_split_forbidden")
        if source.occurred_at >= self.cutoff:
            reasons.append("future_or_untimed_source")
        if source.artifact.sha256 in self.excluded_artifact_hashes:
            reasons.append("heldout_artifact")
        if source.duplicate_group and source.duplicate_group in self.excluded_duplicate_groups:
            reasons.append("heldout_duplicate_group")
        if self.allowed_repos and source.repo_id not in self.allowed_repos:
            reasons.append("source_repo_forbidden")
        return tuple(reasons)

    def reasons(self, record: MemoryRecord) -> tuple[str, ...]:
        reasons = []
        if not record.sources:
            reasons.append("missing_provenance")
        for source in record.sources:
            reasons.extend(self.source_reasons(source))
        for verification in record.validation:
            if verification.artifact not in self.allowed_validation_artifacts:
                reasons.append("validation_not_allowlisted")
            if verification.checked_at >= self.cutoff:
                reasons.append("future_validation")
        return tuple(sorted(set(reasons)))


def validate_build_manifest(policy: SourcePolicy) -> None:
    """Reject contaminated manifests even if a bad source has not yet been retrieved."""
    reasons = {
        reason for source in policy.allowed_sources for reason in policy.source_reasons(source)
    }
    if reasons:
        raise ValueError("invalid_source_manifest:" + ",".join(sorted(reasons)))
