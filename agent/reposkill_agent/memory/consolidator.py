"""Build memory records from run outputs."""

from __future__ import annotations

import hashlib

from reposkill_agent.core.contracts import GraphRunResult, RepoInspection, TaskSpec
from reposkill_agent.memory.episodic import EpisodicMemory
from reposkill_agent.memory.matching import (
    DOMAIN_TAGS,
    python_source_files,
    repo_convention_for_path,
)
from reposkill_agent.memory.procedural import ProceduralMemory
from reposkill_agent.memory.repo_profile import RepoProfileMemory


class MemoryConsolidator:
    """Convert run artifacts into memory objects."""

    @staticmethod
    def repo_fingerprint(task: TaskSpec) -> str:
        return hashlib.sha256(task.repo_path.encode("utf-8")).hexdigest()[:16]

    def build_episodic(self, run: GraphRunResult) -> EpisodicMemory:
        failure_type = None
        if not run.metrics.success:
            failure_type = self._infer_failure_type(run)
        test_output = f"{run.test_result.stdout}\n{run.test_result.stderr}".strip()
        return EpisodicMemory(
            task_id=run.task.id,
            repo_fingerprint=self.repo_fingerprint(run.task),
            issue_summary=run.task.issue[:240],
            plan_summary=self._summarize_plan(run),
            actions=run.actions,
            final_diff_summary=run.diff[:1200],
            tests=[run.test_result.model_dump()],
            outcome="success" if run.metrics.success else "failure",
            failure_type=failure_type,
            test_output_snippet=test_output[:1500],
            expected_files=run.task.expected_files,
            tags=run.task.tags,
        )

    def build_procedural(self, run: GraphRunResult) -> ProceduralMemory | None:
        if not run.metrics.success:
            return None
        domain = [tag for tag in run.task.tags if tag in DOMAIN_TAGS]
        applies = domain or [tag for tag in run.task.tags if tag not in {"support"}]
        diff_hint = run.diff[:400].replace("\n", " ").strip()
        touched = ", ".join(run.task.expected_files[:3])
        pattern = f"Fixed: {run.task.issue[:160]}"
        if run.task.expected_files:
            pattern = f"{pattern} | touched {touched}"
        return ProceduralMemory(
            id=f"proc-{run.task.id}",
            source_task_ids=[run.task.id],
            pattern=pattern,
            reusable_workflow=[
                (
                    f"inspect {run.task.expected_files[0]}"
                    if run.task.expected_files
                    else "inspect repo"
                ),
                "patch expected_files with minimal full-file edits",
                f"run `{run.task.test_command}`",
            ],
            applies_when=applies,
            verifier="tests_pass",
            confidence=0.85,
            likely_files=run.task.expected_files[:4],
            repo_convention=repo_convention_for_path(run.task.repo_path),
            diff_hint=diff_hint,
        )

    def build_repo_profile(self, task: TaskSpec, inspection: RepoInspection) -> RepoProfileMemory:
        from pathlib import Path

        listed: list[str] = []
        root = Path(inspection.repo_path)
        if root.exists():
            listed = python_source_files(
                [
                    path.relative_to(root).as_posix()
                    for path in root.rglob("*.py")
                    if "__pycache__" not in path.parts and "tests" not in path.parts
                ][:40]
            )
        if not listed:
            listed = python_source_files(task.expected_files)
        convention = repo_convention_for_path(task.repo_path)
        style_notes = [convention] if convention else []
        return RepoProfileMemory(
            repo_fingerprint=self.repo_fingerprint(task),
            test_commands=[task.test_command],
            top_level_entries=inspection.top_level_entries,
            common_files=listed or task.expected_files[:6],
            style_notes=style_notes,
        )

    @staticmethod
    def _summarize_plan(run: GraphRunResult) -> str:
        if run.metrics.success and run.diff.strip():
            return f"patched {', '.join(run.task.expected_files[:3])}; tests passed"
        if run.test_result.stdout:
            return run.test_result.stdout[:200].replace("\n", " ")
        return "graph plan executed"

    @staticmethod
    def _infer_failure_type(run: GraphRunResult) -> str:
        if run.test_result.exit_code != 0:
            return "test_failure"
        if not run.diff:
            return "patch_missing"
        return "unknown"
