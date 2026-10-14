"""Skill applicability validator with evidence gating (SkillCard v2)."""

from __future__ import annotations

from reposkill_agent.core.contracts import TaskSpec
from reposkill_agent.skills.domain import domain_compatible, only_generic_evidence
from reposkill_agent.skills.models import SkillEvidenceContext, SkillSelection, SkillSpec

MAX_INJECTED_SKILLS = 2
NEGATIVE_TRANSFER_FAILURE_THRESHOLD = 1

# Map evidence tokens to task tags that satisfy them (Phase 7 aliases).
EVIDENCE_TAG_ALIASES: dict[str, frozenset[str]] = {
    "api": frozenset({"api", "multi_file_api"}),
    "traceback": frozenset({"traceback", "traceback_repair"}),
    "multi_file_api": frozenset({"multi_file_api"}),
    "traceback_repair": frozenset({"traceback_repair"}),
    "skill_heavy": frozenset({"skill_heavy"}),
    "memory_heavy": frozenset({"memory_heavy"}),
    "context_heavy": frozenset({"context_heavy"}),
    "repo_convention": frozenset({"repo_convention"}),
    "inventory": frozenset({"inventory"}),
    "config": frozenset({"config"}),
    "events": frozenset({"events"}),
    "auth": frozenset({"auth"}),
}


class SkillValidator:
    """Validate and gate skills before prompt injection."""

    def validate(
        self,
        task: TaskSpec,
        candidates: list[SkillSpec],
        evidence: SkillEvidenceContext | None = None,
    ) -> SkillSelection:
        """Filter candidates using evidence, negative-transfer, and injection cap."""
        ctx = evidence or SkillEvidenceContext(
            issue=task.issue,
            tags=task.tags,
            expected_files=task.expected_files,
        )
        selected: list[SkillSpec] = []
        rejected: list[dict[str, str]] = []
        for skill in candidates:
            reject_reason = self._reject_reason(skill, task, ctx)
            if reject_reason:
                rejected.append({"skill_id": skill.id, "reason": reject_reason})
                continue
            selected.append(skill)

        injected = selected[:MAX_INJECTED_SKILLS]
        gated = len(candidates) - len(injected)
        return SkillSelection(
            selected=injected,
            retrieved_count=len(candidates),
            validated_count=len(selected),
            candidate_count=len(candidates),
            injected_count=len(injected),
            gated_count=gated,
            rejected=rejected,
        )

    def _reject_reason(
        self,
        skill: SkillSpec,
        task: TaskSpec,
        evidence: SkillEvidenceContext,
    ) -> str | None:
        issue_lower = task.issue.lower()
        tag_blob = " ".join(task.tags).lower()
        for anti in skill.anti_patterns:
            if anti.lower() in issue_lower:
                return f"anti_pattern:{anti}"
        if not domain_compatible(skill, task):
            if only_generic_evidence(skill):
                return "domain_mismatch_generic_evidence"
            return "domain_mismatch"
        for bad in skill.not_applicable_when:
            if bad.lower() in issue_lower:
                return f"not_applicable:{bad}"
        if skill.applies_when and not any(x.lower() in issue_lower for x in skill.applies_when):
            if not any(x.lower() in tag_blob for x in skill.applies_when):
                return "applies_when_miss"
        if self._has_negative_transfer(skill):
            return "negative_transfer"
        missing = [
            item
            for item in skill.evidence_requirements()
            if not self._evidence_present(item, evidence, skill)
        ]
        if missing:
            return f"missing_evidence:{','.join(missing)}"
        return None

    @staticmethod
    def _has_negative_transfer(skill: SkillSpec) -> bool:
        if len(skill.negative_transfer_notes) >= 2:
            return True
        return (
            skill.failure_count > skill.success_count
            and skill.failure_count >= NEGATIVE_TRANSFER_FAILURE_THRESHOLD
        )

    @staticmethod
    def _normalized_token(token: str) -> str:
        return token.lower().replace(" ", "_")

    @classmethod
    def _evidence_present(
        cls,
        token: str,
        evidence: SkillEvidenceContext,
        skill: SkillSpec,
    ) -> bool:
        token_norm = cls._normalized_token(token)
        tag_set = set(evidence.tags)

        alias_tags = EVIDENCE_TAG_ALIASES.get(token_norm)
        if alias_tags and alias_tags & tag_set:
            return True

        haystacks = [
            evidence.issue.lower(),
            " ".join(evidence.tags).lower(),
            evidence.test_output.lower(),
            " ".join(evidence.expected_files).lower(),
            " ".join(evidence.locator_matches).lower(),
            " ".join(evidence.repo_files).lower(),
        ]
        if token_norm in {"expected_files", "expected files"}:
            return bool(evidence.expected_files)
        if token_norm == "tags":
            return bool(evidence.tags)
        if token_norm in {"repo_files", "repo files"}:
            return bool(evidence.repo_files)
        if token_norm in {"test_output", "test output"}:
            if evidence.test_output.strip():
                return True
            # Pre-first-patch: traceback tasks may gate on traceback_repair tag only.
            if "traceback_repair" in tag_set and cls._requires_traceback_output(skill):
                return True
            return False
        if token_norm in {"traceback", "pytest"}:
            if evidence.test_output.strip():
                return True
            return bool({"traceback", "traceback_repair"} & tag_set)
        return any(token_norm.replace("_", " ") in hay for hay in haystacks)

    @staticmethod
    def _requires_traceback_output(skill: SkillSpec) -> bool:
        requirements = {item.lower().replace(" ", "_") for item in skill.evidence_requirements()}
        return "traceback" in requirements or "test_output" in requirements
