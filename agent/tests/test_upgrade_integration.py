import json
from datetime import timedelta

import pytest
from typer.testing import CliRunner

from reposkill_agent.cli import app
from reposkill_agent.eval.upgrade_demo import run_demo
from reposkill_agent.evidence.models import Observation
from reposkill_agent.evidence.strategy import plan_public_step
from reposkill_agent.memory.builder import PublicTrajectory, build_candidate
from reposkill_agent.memory.record_store import RecordStore
from reposkill_agent.memory.records import MemoryRecord
from reposkill_agent.protocol.public import decode_public_task
from tests.upgrade_helpers import NOW, PAST, artifact, policy, record, source, task, validated


def test_rule_builder_requires_public_allowlisted_bytes():
    text = PublicTrajectory(
        issue_summary="parse_config",
        public_evidence=("public test",),
        actions=("inspect parser",),
        public_verification="public tests",
    ).model_dump_json()
    src = source(artifact=artifact(text))
    p = policy(allowed_sources=(src,))
    result = build_candidate(text, src, p, now=PAST)
    assert result.status == "candidate"
    assert result.build_usage.calls == 0
    with pytest.raises(ValueError, match="content_changed"):
        build_candidate(text + " ", src, p, now=PAST)


def test_public_pipeline_oracle_noninterference_and_noop():
    t, _ = decode_public_task(task().model_dump(mode="json"))
    text = "def parse_config(text): return {}"
    obs = Observation(
        observation_id="read",
        kind="file",
        path="parser.py",
        content=text,
        repo_revision="v1",
        artifact=artifact(text, run="current"),
    )
    plain = plan_public_step(t, ("parser.py",), observations=(obs,))
    empty = plan_public_step(t, ("parser.py",), observations=(obs,), records=())
    assert plain == empty
    assert plain["memory_decision"] is None
    assert "expected_files" not in json.dumps(plain)
    # Public DTO never contains the private metadata changed by an evaluator.
    for private_gold in ("SENTINEL_A", "SENTINEL_B"):
        assert private_gold not in json.dumps(plain)


def test_demo_expected_drift_matrix_and_no_real_success_claim(tmp_path):
    result = run_demo(tmp_path / "demo")
    assert result["repair_success"] is None
    assert result["external_model_calls"] == 0
    assert result["actual_model_injection"] is False
    assert "ORACLE_DEMO_SENTINEL" not in json.dumps(result)
    outcomes = {(r["case"], r["variant"]): r["selected"] for r in result["drift_matrix"]}
    assert outcomes["unchanged", "D3_dependency"]
    assert not outcomes["api_changed", "D3_dependency"]
    assert not outcomes["package_changed_same_commit", "D3_dependency"]
    assert outcomes["unrelated_file_changed", "D3_dependency"]
    assert not outcomes["unrelated_file_changed", "D2_clear_on_change"]
    assert not outcomes["unknown_dependency", "D3_dependency"]
    assert all(u["following"] == "unknown" for u in result["usage_audit"]["uses"])
    from reposkill_agent.protocol.public import digest

    current = result["memory_snapshot"]["records"][0]
    refs = [s["artifact"] for s in current["sources"]]
    refs += [v["artifact"] for v in current["validation"]]
    for reference in refs:
        assert (
            digest((tmp_path / "demo" / reference["relative_path"]).read_bytes())
            == (reference["sha256"])
        )
    assert result["fixture_receipts"][0]["decision_id"] == result["receipt_decision"]["decision_id"]
    with pytest.raises(FileExistsError):
        run_demo(tmp_path / "demo")


def test_cli_demo_and_help(tmp_path):
    runner = CliRunner()
    help_result = runner.invoke(app, ["upgrade-demo", "--help"])
    assert help_result.exit_code == 0
    result = runner.invoke(app, ["upgrade-demo", "--output", str(tmp_path / "cli")])
    assert result.exit_code == 0, result.output
    assert "model calls=0" in result.output
    assert (tmp_path / "cli/result.json").exists()


def test_store_refuses_existing_legacy_database(tmp_path):
    import sqlite3

    path = tmp_path / "legacy.db"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE episodic_index (id INTEGER)")
    with pytest.raises(ValueError, match="legacy_store"):
        RecordStore(path)


def test_semantic_revision_needs_new_public_validation(tmp_path):
    store = RecordStore(tmp_path / "memory.db")
    store.append(record(), reason="build")
    store.append(validated(), reason="verified", policy=policy())
    payload = validated().model_dump()
    payload.update(revision=3, supersedes=2, applicability=("new scope",))
    with pytest.raises(ValueError, match="revalidation_required"):
        store.append(MemoryRecord(**payload), reason="scope change", policy=policy())


def test_future_and_relabelled_validation_rejected():
    bad = validated(
        last_validated_at=NOW + timedelta(days=1),
        validation=(
            validated().validation[0].model_copy(update={"checked_at": NOW + timedelta(days=1)}),
        ),
    )
    assert "future_validation" in policy().reasons(bad)


def test_new_legacy_reports_remain_explicitly_diagnostic(tmp_path):
    from reposkill_agent.eval.llm_ablation import LLMAblationRunner
    from reposkill_agent.eval.report import write_llm_ablation_markdown
    from reposkill_agent.eval.task_spec import TaskCatalog
    from reposkill_agent.llm.client import MockModelClient

    runner = LLMAblationRunner(tmp_path / "llm", MockModelClient())
    summary = runner.run(TaskCatalog(tasks=[]), config_names=[])
    assert summary["protocol_mode"] == "diagnostic_oracle"
    # Report writer requires per-config aggregates; no need to execute legacy tasks.
    summary["results"] = {}
    path = tmp_path / "report.md"
    write_llm_ablation_markdown(summary, path)
    assert "diagnostic_oracle" in path.read_text(encoding="utf-8")
