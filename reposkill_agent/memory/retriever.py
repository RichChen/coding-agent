"""Memory retrieval with MemoryHint v2 gating."""

from __future__ import annotations

from reposkill_agent.core.contracts import TaskSpec
from reposkill_agent.memory.episodic import EpisodicStore
from reposkill_agent.memory.matching import (
    extract_test_signals,
    procedural_applies,
    repo_convention_for_path,
    seed_pair_task_id,
)
from reposkill_agent.memory.models import MemoryHint, MemorySelection
from reposkill_agent.memory.procedural import ProceduralStore
from reposkill_agent.memory.repo_profile import RepoProfileStore

MAX_INJECTED_HINTS = 3


class MemoryRetriever:
    """Retrieve and gate compact memory hints for the current task."""

    def __init__(
        self,
        episodic_store: EpisodicStore,
        procedural_store: ProceduralStore,
        repo_profile_store: RepoProfileStore,
    ) -> None:
        self.episodic_store = episodic_store
        self.procedural_store = procedural_store
        self.repo_profile_store = repo_profile_store

    def select(
        self,
        task: TaskSpec,
        repo_fingerprint: str,
        *,
        max_hints: int = MAX_INJECTED_HINTS,
        repo_profile_only: bool = False,
        exclude_episodic_failures: bool = False,
        procedural_only: bool = False,
        test_output: str = "",
        exclude_repo_profile: bool = False,
    ) -> MemorySelection:
        """Return gated MemoryHint v2 payloads for prompt injection."""
        candidates = self._collect_candidates(
            task,
            repo_fingerprint,
            exclude_episodic_failures=exclude_episodic_failures,
            procedural_only=procedural_only,
            test_output=test_output,
        )
        ranked = self._rank_candidates(candidates, task)
        if repo_profile_only:
            ranked = [hint for hint in ranked if hint.type == "repo_profile"]
        elif exclude_repo_profile:
            ranked = [hint for hint in ranked if hint.type != "repo_profile"]
        injected = ranked[:max_hints]
        return MemorySelection(
            injected=[hint.to_prompt_dict() for hint in injected],
            candidate_count=len(candidates),
            injected_count=len(injected),
            gated_count=max(0, len(candidates) - len(injected)),
            source_task_ids=sorted(
                {hint.source_task_id for hint in injected if hint.source_task_id}
            ),
        )

    def retrieve(self, task: TaskSpec, repo_fingerprint: str) -> list[dict]:
        """Backward-compatible retrieve API returning injected hint dicts."""
        return self.select(task, repo_fingerprint).injected

    def _collect_candidates(
        self,
        task: TaskSpec,
        repo_fingerprint: str,
        *,
        exclude_episodic_failures: bool = False,
        procedural_only: bool = False,
        test_output: str = "",
    ) -> list[MemoryHint]:
        hints: list[MemoryHint] = []
        convention = repo_convention_for_path(task.repo_path)
        profile = self.repo_profile_store.get(repo_fingerprint)
        likely_files = task.expected_files[:4]
        if profile is not None and profile.common_files:
            likely_files = profile.common_files[:5]
        profile_convention = convention
        if profile is not None and profile.style_notes:
            profile_convention = "; ".join(profile.style_notes[:2])
        hints.append(
            MemoryHint(
                type="repo_profile",
                source_task_id=repo_fingerprint,
                confidence=0.92,
                applies_when=task.tags,
                likely_files=likely_files,
                successful_pattern="edit expected_files; run declared test_command",
                repo_convention=profile_convention or convention,
            )
        )
        seed_id = seed_pair_task_id(task.id)
        for item in self.procedural_store.list_all():
            if not procedural_applies(item.applies_when, task):
                continue
            seed_boost = seed_id and seed_id in item.source_task_ids
            hints.append(
                MemoryHint(
                    type="procedural",
                    source_task_id=item.source_task_ids[0] if item.source_task_ids else item.id,
                    confidence=0.9 if seed_boost else item.confidence,
                    applies_when=item.applies_when,
                    likely_files=item.likely_files or task.expected_files[:3],
                    successful_pattern=item.pattern,
                    repo_convention=item.repo_convention or item.diff_hint[:180],
                )
            )
        for item in self.episodic_store.list_recent(limit=12):
            if procedural_only:
                continue
            if item.repo_fingerprint != repo_fingerprint:
                continue
            if item.task_id == task.id:
                continue
            if item.outcome != "success":
                if exclude_episodic_failures:
                    continue
                hints.append(
                    MemoryHint(
                        type="episodic",
                        source_task_id=item.task_id,
                        confidence=0.3,
                        applies_when=item.tags or task.tags,
                        likely_files=item.expected_files[:3] or task.expected_files[:2],
                        successful_pattern=item.issue_summary[:120],
                        warning=f"prior failure: {item.failure_type or 'unknown'}",
                    )
                )
                continue
            hints.append(
                MemoryHint(
                    type="episodic",
                    source_task_id=item.task_id,
                    confidence=0.82 if seed_id and item.task_id == seed_id else 0.72,
                    applies_when=item.tags or task.tags,
                    likely_files=item.expected_files[:3] or task.expected_files[:2],
                    successful_pattern=item.plan_summary[:160] or item.issue_summary[:120],
                    repo_convention=item.final_diff_summary[:160],
                )
            )
        signal_hint = self._test_signal_hint(task, test_output)
        if signal_hint is not None:
            hints.append(signal_hint)
        return hints

    @staticmethod
    def _test_signal_hint(task: TaskSpec, test_output: str) -> MemoryHint | None:
        signals = extract_test_signals(test_output)
        if not signals:
            return None
        return MemoryHint(
            type="procedural",
            source_task_id="current_test_output",
            confidence=0.95,
            applies_when=task.tags,
            likely_files=task.expected_files[:3],
            successful_pattern="; ".join(signals),
            repo_convention=repo_convention_for_path(task.repo_path),
        )

    @staticmethod
    def _rank_candidates(candidates: list[MemoryHint], task: TaskSpec) -> list[MemoryHint]:
        priority = {"procedural": 0, "repo_profile": 1, "episodic": 2}
        seed_id = seed_pair_task_id(task.id)

        def sort_key(hint: MemoryHint) -> tuple[int, int, float]:
            warn_penalty = 1 if hint.warning else 0
            seed_boost = 0 if seed_id and hint.source_task_id == seed_id else 1
            test_signal_boost = 0 if hint.source_task_id == "current_test_output" else 1
            return (
                test_signal_boost,
                seed_boost,
                priority.get(hint.type, 9),
                warn_penalty,
                -hint.confidence,
            )

        return sorted(candidates, key=sort_key)
