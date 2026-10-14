"""Synthetic, public fixtures for upgrade tests (never production provenance)."""

from datetime import UTC, datetime

from reposkill_agent.memory.records import (
    BuildUsage,
    Dependency,
    MemoryRecord,
    SourceRef,
    ValidationEvidence,
)
from reposkill_agent.memory.source_manifest import SourcePolicy
from reposkill_agent.memory.validity import Fact, RepoFacts
from reposkill_agent.protocol.public import ArtifactRef, Budget, PublicTask, RepoRef, digest

PAST = datetime(2026, 9, 1, tzinfo=UTC)
NOW = datetime(2026, 9, 19, tzinfo=UTC)


def artifact(text="public fixture", name="source", run="source-run"):
    return ArtifactRef(
        logical_id=name,
        sha256=digest(text),
        size_bytes=len(text.encode()),
        run_id=run,
        relative_path=f"artifacts/{name}.txt",
    )


def task(**changes):
    data = dict(
        task_id="opaque-target",
        issue_text="parse_config fails on empty config",
        repo_ref=RepoRef(repo_id="fixture-repo", revision="v1"),
        workspace_id="fixture-workspace",
        allowed_tools=("read", "search", "patch"),
        execution_profile_ref="fixture-only",
        budget=Budget(
            wall_seconds=60, model_calls=0, input_tokens=0, output_tokens=0, tool_calls=8
        ),
    )
    data.update(changes)
    return PublicTask(**data)


def source(**changes):
    data = dict(
        task_id="past-task",
        run_id="source-run",
        repo_id="fixture-repo",
        repo_revision="v1",
        protocol_mode="realistic",
        split="memory_build",
        occurred_at=PAST,
        artifact=artifact(),
        duplicate_group="past-group",
    )
    data.update(changes)
    return SourceRef(**data)


def policy(**changes):
    data = dict(
        allowed_sources=(source(),),
        target_task_ids=("opaque-target",),
        allowed_validation_artifacts=(artifact("1 passed", "verification"),),
        cutoff=NOW,
    )
    data.update(changes)
    return SourcePolicy(**data)


def record(**changes):
    text = "For empty config, inspect parse_config and run public parser tests."
    data = dict(
        memory_id="memory-parser",
        kind="procedure",
        content_hash=digest(text),
        procedure=text,
        verification_recipe="public parser tests",
        source_repo_id="fixture-repo",
        sources=(source(),),
        created_at=PAST,
        build_usage=BuildUsage(method="human-authored", cost=0, currency="USD"),
        dependencies=(
            Dependency(
                kind="api_signature", key="parse_config", expected="(text)", evidence_ref="source"
            ),
        ),
        dependency_mapping_complete=True,
    )
    data.update(changes)
    return MemoryRecord(**data)


def validated(**changes):
    data = dict(
        status="validated",
        revision=2,
        supersedes=1,
        last_validated_at=PAST,
        validation=(
            ValidationEvidence(
                artifact=artifact("1 passed", "verification"),
                repo_id="fixture-repo",
                repo_revision="v1",
                checked_at=PAST,
                collected=1,
                passed=1,
                outcome="pass",
            ),
        ),
    )
    data.update(changes)
    return record(**data)


def facts(**changes):
    data = dict(
        repo_id="fixture-repo",
        revision="v1",
        observed_at=NOW,
        facts=(
            Fact(
                kind="api_signature",
                key="parse_config",
                value="(text)",
                evidence_ref="current-source",
                repo_revision="v1",
            ),
        ),
    )
    data.update(changes)
    return RepoFacts(**data)
