"""Pre-harness realistic routing, checkpoint, and offline runner contracts."""

import ast
import json
from pathlib import Path

import pytest

from reposkill_agent.eval.public_runner import run_public_rounds
from reposkill_agent.evidence.models import EvidenceState, Observation
from reposkill_agent.evidence.strategy import (
    restore_strategy_state,
    serialize_strategy_state,
    strategy_state_for,
)
from reposkill_agent.memory.builder import PublicTrajectory, build_candidate
from reposkill_agent.memory.records import MemoryRecord
from reposkill_agent.skills.models import SkillSpec
from reposkill_agent.skills.public_router import route_public_skills
from tests.upgrade_helpers import NOW, PAST, artifact, facts, policy, source, task


def _observation(text: str = "def parse_config(text): return {}") -> Observation:
    return Observation(
        observation_id="parser-read",
        kind="file",
        path="parser.py",
        content=text,
        repo_revision="v1",
        artifact=artifact(text, "parser", "current-run"),
    )


def test_public_router_uses_observed_evidence_without_legacy_tags():
    public_task = task(issue_text="parse_config fails on empty config")
    evidence = EvidenceState(
        repo_revision="v1", observations=(_observation(),), hypotheses=("parser.py",)
    )
    skill = SkillSpec(
        id="parse_config_skill",
        name="Parser repair",
        version="1",
        purpose="repair parse_config API behavior",
        required_evidence=["parse_config"],
        edit_recipe=["inspect parser"],
    )
    route = route_public_skills(public_task, evidence, facts(), [skill])
    assert [item.skill_id for item in route.selected] == ["parse_config_skill"]
    # A private evaluator sentinel in task_id cannot affect lexical routing.
    changed = task(task_id="SENTINEL_A", issue_text=public_task.issue_text)
    changed_route = route_public_skills(changed, evidence, facts(), [skill])
    assert changed_route.model_dump() == route.model_dump()


def test_public_router_allows_zero_skills_and_rejects_missing_evidence():
    public_task = task()
    evidence = EvidenceState(repo_revision="v1")
    skill = SkillSpec(
        id="trace_skill",
        name="Trace repair",
        version="1",
        purpose="repair traceback",
        required_evidence=["traceback text"],
    )
    route = route_public_skills(public_task, evidence, facts(), [skill])
    assert not route.selected
    assert route.rejected[0]["reason"] == "missing_public_evidence"


def test_strategy_state_round_trip_is_pure_and_bound_to_task():
    public_task = task()
    state = strategy_state_for(
        public_task,
        EvidenceState(repo_revision="v1"),
        memory_snapshot_id="snapshot-1",
        proposal_ids=("proposal-1",),
        receipt_cursor="receipt-2",
    )
    encoded = serialize_strategy_state(state)
    restored = restore_strategy_state(public_task, encoded, memory_snapshot_id="snapshot-1")
    assert restored == state
    assert json.loads(encoded)["schema_version"] == "1.0"
    with pytest.raises(ValueError, match="task_mismatch"):
        restore_strategy_state(task(task_id="other"), encoded)
    with pytest.raises(ValueError, match="memory_snapshot"):
        restore_strategy_state(public_task, encoded, memory_snapshot_id="other")


def test_offline_runner_walks_fixture_observations_without_tools_or_models():
    public_task = task()
    result = run_public_rounds(
        public_task,
        ("parser.py",),
        observation_rounds=((), (_observation(),)),
    )
    assert len(result.rounds) == 2
    assert result.external_model_calls == 0
    assert result.tool_calls_executed == 0
    assert json.loads(result.rounds[-1].state)["repo_revision"] == "v1"
    assert result.rounds[-1].result["locator"]["status"] == "evidence_ready"


def test_public_trajectory_preserves_failures_and_stays_candidate():
    text = PublicTrajectory(
        issue_summary="parse_config",
        public_evidence=("public parser test",),
        actions=("inspect parser",),
        public_verification="public tests",
        failure_notes=("first attempt changed unrelated file",),
    ).model_dump_json()
    src = source(artifact=artifact(text, "trajectory"))
    candidate = build_candidate(text, src, policy(allowed_sources=(src,)), now=PAST)
    assert candidate.status == "candidate"
    assert "first attempt changed unrelated file" in candidate.procedure
    with pytest.raises(ValueError, match="missing_public_validation"):
        payload = candidate.model_dump()
        payload["status"] = "validated"
        MemoryRecord(**payload)


@pytest.mark.parametrize(
    "source_change, policy_change",
    [
        ({"split": "heldout"}, {}),
        ({"protocol_mode": "diagnostic_oracle"}, {}),
        ({"occurred_at": NOW}, {}),
        ({"duplicate_group": "blocked"}, {"excluded_duplicate_groups": ("blocked",)}),
    ],
)
def test_public_trajectory_rejects_non_build_sources(source_change, policy_change):
    text = PublicTrajectory(
        issue_summary="parse_config",
        public_evidence=("public test",),
        actions=("inspect",),
        public_verification="public tests",
    ).model_dump_json()
    src = source(artifact=artifact(text, "bad-source"), **source_change)
    with pytest.raises(ValueError, match="invalid_source_manifest|trajectory_source_rejected"):
        build_candidate(text, src, policy(allowed_sources=(src,), **policy_change), now=PAST)


def test_public_trajectory_rejects_oracle_fields():
    text = (
        '{"issue_summary":"x","public_evidence":[],"actions":[],'
        '"public_verification":"ok","expected_files":["private.py"]}'
    )
    src = source(artifact=artifact(text, "oracle-trajectory"))
    with pytest.raises(ValueError, match="oracle_field_present"):
        build_candidate(text, src, policy(allowed_sources=(src,)), now=PAST)


def test_realistic_modules_have_no_legacy_task_imports():
    root = Path("reposkill_agent")
    modules = (
        root / "skills" / "public_router.py",
        root / "evidence" / "strategy.py",
        root / "eval" / "public_runner.py",
    )
    for path in modules:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        assert "TaskSpec" not in imported
        assert "TaskCategory" not in imported
