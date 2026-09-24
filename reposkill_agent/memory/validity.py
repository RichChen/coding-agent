"""Pure, explainable dependency checks over host-supplied public facts."""

from datetime import datetime
from typing import Literal

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version
from pydantic import AwareDatetime

from reposkill_agent.memory.records import MemoryRecord
from reposkill_agent.protocol.public import StrictModel


class Fact(StrictModel):
    kind: Literal["api_signature", "package", "file_hash"]
    key: str
    value: str
    evidence_ref: str
    repo_revision: str
    extractor_version: str = "1"


class RepoFacts(StrictModel):
    repo_id: str
    revision: str
    observed_at: AwareDatetime
    facts: tuple[Fact, ...] = ()


class Check(StrictModel):
    dependency_key: str
    status: Literal["valid", "invalid", "unknown"]
    reason: str
    evidence_refs: tuple[str, ...] = ()


class ValidityResult(StrictModel):
    status: Literal["valid", "invalid", "unknown"]
    checks: tuple[Check, ...]
    checker_version: str = "dependency-rules-1"
    external_model_calls: int = 0


def check_validity(record: MemoryRecord, facts: RepoFacts, now: datetime) -> ValidityResult:
    if now.tzinfo is None:
        raise ValueError("aware_clock_required")
    checks = []
    if record.source_repo_id != facts.repo_id:
        checks.append(Check(dependency_key="repo", status="invalid", reason="repo_mismatch"))
    if facts.observed_at > now:
        checks.append(Check(dependency_key="clock", status="unknown", reason="future_observation"))
    if not record.dependency_mapping_complete or not record.dependencies:
        checks.append(
            Check(
                dependency_key="mapping", status="unknown", reason="incomplete_dependency_mapping"
            )
        )
    if record.last_validated_at is None:
        checks.append(
            Check(dependency_key="validation", status="unknown", reason="missing_validation")
        )
    elif record.last_validated_at > now:
        checks.append(
            Check(dependency_key="validation", status="unknown", reason="future_validation")
        )
    elif (
        record.ttl_seconds and (now - record.last_validated_at).total_seconds() > record.ttl_seconds
    ):
        checks.append(Check(dependency_key="ttl", status="unknown", reason="revalidation_due"))
    for dep in record.dependencies:
        matches = [
            f
            for f in facts.facts
            if f.kind == dep.kind
            and f.key == dep.key
            and f.repo_revision == facts.revision
            and f.extractor_version == dep.extractor_version
            and f.evidence_ref
        ]
        values = {f.value for f in matches}
        refs = tuple(sorted({f.evidence_ref for f in matches}))
        state, reason = "unknown", "missing_or_conflicting_fact"
        if len(values) == 1:
            value = next(iter(values))
            if dep.kind == "package":
                try:
                    compatible = Version(value) in SpecifierSet(dep.expected)
                    state = "valid" if compatible else "invalid"
                    reason = "package_compatible" if compatible else "package_incompatible"
                except (InvalidSpecifier, InvalidVersion):
                    reason = "unsupported_package_version"
            elif value == dep.expected:
                state, reason = "valid", "dependency_unchanged"
            elif dep.kind == "api_signature":
                state, reason = "invalid", "api_signature_changed"
            else:
                reason = "file_changed_semantics_unknown"
        checks.append(
            Check(dependency_key=dep.key, status=state, reason=reason, evidence_refs=refs)
        )
    status = (
        "invalid"
        if any(c.status == "invalid" for c in checks)
        else "unknown"
        if any(c.status == "unknown" for c in checks)
        else "valid"
    )
    return ValidityResult(status=status, checks=tuple(checks))
