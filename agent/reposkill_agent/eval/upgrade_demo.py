"""Synthetic offline walkthrough. No runtime, model call, or success-rate claim."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from reposkill_agent.eval.public_export import ExportFile, ExportManifest, export_public_workspace
from reposkill_agent.evidence.models import Observation
from reposkill_agent.evidence.strategy import plan_public_step
from reposkill_agent.memory.builder import PublicTrajectory, build_candidate
from reposkill_agent.memory.gate import InjectionReceipt, confirm_injection, select_memory
from reposkill_agent.memory.record_store import RecordStore
from reposkill_agent.memory.records import Dependency, MemoryRecord, SourceRef, ValidationEvidence
from reposkill_agent.memory.source_manifest import SourcePolicy
from reposkill_agent.memory.validity import Fact, RepoFacts
from reposkill_agent.protocol.evaluation import EvaluationSpec
from reposkill_agent.protocol.public import (
    ArtifactRef,
    Budget,
    PublicTask,
    RepoRef,
    canonical,
    digest,
)

PAST = datetime(2026, 9, 1, tzinfo=UTC)
NOW = datetime(2026, 9, 19, tzinfo=UTC)


def ref(text: str, name: str, run: str = "past-run") -> ArtifactRef:
    return ArtifactRef(
        logical_id=name,
        sha256=digest(text),
        size_bytes=len(text.encode()),
        run_id=run,
        relative_path=f"artifacts/{name}.txt",
    )


def demo_inputs():
    task = PublicTask(
        task_id="demo-target",
        issue_text="parse_config in parser.py rejects empty config",
        repo_ref=RepoRef(repo_id="demo-repo", revision="v1"),
        workspace_id="public-demo",
        execution_profile_ref="offline-fixture-only",
        allowed_tools=("read", "search", "patch", "public_test"),
        budget=Budget(
            wall_seconds=60, model_calls=0, input_tokens=0, output_tokens=0, tool_calls=8
        ),
    )
    text = PublicTrajectory(
        issue_summary="parse_config handles empty config",
        public_evidence=("Public parser test failed on empty input.",),
        actions=("Inspect parse_config signature and normalize empty input.",),
        public_verification="Run the public parser test.",
    ).model_dump_json()
    source = SourceRef(
        task_id="past-demo",
        run_id="past-run",
        repo_id="demo-repo",
        repo_revision="v1",
        protocol_mode="realistic",
        split="memory_build",
        occurred_at=PAST,
        artifact=ref(text, "trajectory"),
    )
    verification = ref("fixture public test: 1 collected, 1 passed", "verification")
    policy = SourcePolicy(
        allowed_sources=(source,),
        allowed_validation_artifacts=(verification,),
        target_task_ids=(task.task_id,),
        cutoff=NOW,
    )
    candidate = build_candidate(
        text,
        source,
        policy,
        now=PAST,
        dependency_mapping_complete=True,
        dependencies=(
            Dependency(
                kind="api_signature",
                key="parse_config",
                expected="(text)",
                evidence_ref="trajectory",
            ),
            Dependency(
                kind="package", key="parserlib", expected=">=1,<2", evidence_ref="trajectory"
            ),
        ),
    )
    validation = ValidationEvidence(
        artifact=verification,
        repo_id="demo-repo",
        repo_revision="v1",
        checked_at=PAST,
        collected=1,
        passed=1,
        outcome="pass",
    )
    validated = MemoryRecord.model_validate(
        {
            **candidate.model_dump(),
            "revision": 2,
            "supersedes": 1,
            "status": "validated",
            "validation": (validation,),
            "last_validated_at": PAST,
        }
    )
    return (
        task,
        policy,
        candidate,
        validated,
        {
            "trajectory": text,
            "verification": "fixture public test: 1 collected, 1 passed",
        },
    )


def drift_facts(revision: str, signature: str | None, package: str = "1.2") -> RepoFacts:
    facts = [
        Fact(
            kind="package",
            key="parserlib",
            value=package,
            evidence_ref="current-lock",
            repo_revision=revision,
        )
    ]
    if signature is not None:
        facts.append(
            Fact(
                kind="api_signature",
                key="parse_config",
                value=signature,
                evidence_ref="current-api",
                repo_revision=revision,
            )
        )
    return RepoFacts(repo_id="demo-repo", revision=revision, observed_at=NOW, facts=tuple(facts))


def drift_matrix(task, record, policy) -> list[dict]:
    # Labels stay evaluator-side; the gate sees only public code/environment facts.
    cases = [
        ("unchanged", drift_facts("v1", "(text)"), "valid"),
        ("api_changed", drift_facts("v2", "(text, strict)"), "stale"),
        ("package_changed_same_commit", drift_facts("v1", "(text)", "2.0"), "stale"),
        ("unrelated_file_changed", drift_facts("v2", "(text)"), "valid"),
        ("unknown_dependency", drift_facts("v2", None), "unknown"),
    ]
    rows = []
    for name, facts, label in cases:
        current_task = task.model_copy(
            update={"repo_ref": RepoRef(repo_id="demo-repo", revision=facts.revision)}
        )
        decision = select_memory(current_task, [record], facts, policy, NOW, decision_id=name)
        # Whole-store clearing compares code AND declared environment facts.
        changed = facts.revision != "v1" or any(
            f.kind == "package" and f.value != "1.2" for f in facts.facts
        )
        for variant, selected in (
            ("D0_no_memory", False),
            ("D1_static", True),
            ("D2_clear_on_change", not changed),
            ("D3_dependency", bool(decision.candidates)),
        ):
            stale_total, valid_total = int(label == "stale"), int(label == "valid")
            rows.append(
                {
                    "case": name,
                    "variant": variant,
                    "candidate_count": 1,
                    "selected": selected,
                    "fixture_host_injected": selected,
                    "stale_candidates": stale_total,
                    "stale_injected": int(selected and stale_total),
                    "valid_candidates": valid_total,
                    "valid_retained": int(selected and valid_total),
                    "stale_injection_rate": int(selected) if stale_total else None,
                    "valid_retention_rate": int(selected) if valid_total else None,
                    "validity": decision.items[0].validity.model_dump(mode="json"),
                    "capability_result": None,
                }
            )
    return rows


def run_demo(output: Path) -> dict:
    """Write only a new user-selected directory; all data is explicitly synthetic."""
    output.mkdir(parents=True, exist_ok=False)
    task, policy, candidate, validated, artifact_texts = demo_inputs()
    source = output / "private-preparation"
    source.mkdir()
    code = (
        "def parse_config(text):\n    return dict(line.split('=') for line in text.splitlines())\n"
    )
    (source / "parser.py").write_text(code, encoding="utf-8", newline="\n")
    (source / "private_test.py").write_text("ORACLE_DEMO_SENTINEL", encoding="utf-8")
    manifest = ExportManifest(
        repo_id="demo-repo",
        revision="v1",
        reviewed_public=True,
        files=(ExportFile(path="parser.py", sha256=digest(code)),),
    )
    public = output / "public-workspace"
    export = export_public_workspace(
        source,
        public,
        task,
        manifest,
        EvaluationSpec(
            task_id=task.task_id,
            gold_patch="ORACLE_DEMO_SENTINEL",
            hidden_test_refs=("private_test.py",),
        ),
    )
    (output / "public-task.json").write_text(task.model_dump_json(indent=2), encoding="utf-8")
    store = RecordStore(output / "memory.db")
    store.append(candidate, reason="allowlisted_public_trajectory")
    store.append(validated, reason="fixture_public_validation", policy=policy)
    observation = Observation(
        observation_id="read-parser",
        kind="file",
        path="parser.py",
        content=code,
        repo_revision="v1",
        artifact=ref(code, "read-parser", "demo-run"),
    )
    artifact_texts["read-parser"] = code
    (output / "artifacts").mkdir()
    for name, text in artifact_texts.items():
        (output / "artifacts" / f"{name}.txt").write_bytes(text.encode("utf-8"))
    (output / "source-policy.json").write_text(policy.model_dump_json(indent=2), encoding="utf-8")
    step = plan_public_step(
        task,
        ("parser.py",),
        observations=(observation,),
        records=tuple(store.records()),
        facts=drift_facts("v1", "(text)"),
        source_policy=policy,
        now=NOW,
    )
    gate = select_memory(
        task, store.records(), drift_facts("v1", "(text)"), policy, NOW, decision_id="receipt-demo"
    )
    receipts = []
    for c in gate.candidates:
        receipts.append(
            InjectionReceipt(
                receipt_id="fixture-" + c.candidate_id,
                decision_id=gate.decision_id,
                candidate_id=c.candidate_id,
                requested_hash=c.requested_hash,
                status="injected",
                end_char=len(c.text),
                actual_hash=digest(c.text),
                model_operation_id="fixture-model-operation",
                model_attempt_id="fixture-attempt",
                reason="fixture_host_only_no_model_called",
            )
        )
    for use in confirm_injection(gate, tuple(receipts), "demo-run"):
        store.record_use(use)
    rows = drift_matrix(task, validated, policy)
    summary = {
        "schema_version": "1.0",
        "protocol_mode": "realistic",
        "evidence_layer": "synthetic_offline",
        "external_model_calls": 0,
        "external_model_cost": 0,
        "currency": "USD",
        "actual_model_injection": False,
        "real_harness_integration": False,
        "repair_success": None,
        "export": export,
        "strategy": step,
        "memory_snapshot": store.snapshot(),
        "usage_audit": store.audit(),
        "receipt_decision": gate.model_dump(mode="json"),
        "fixture_receipts": [receipt.model_dump(mode="json") for receipt in receipts],
        "drift_matrix": rows,
    }
    (output / "result.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    lines = [
        "# Offline upgrade demo",
        "",
        "Synthetic fixture only. No model calls, no real harness, no repair-success claim.",
        "",
        "| Case | Variant | Fixture injected | Stale / candidates | Valid / candidates |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['case']} | {r['variant']} | {r['fixture_host_injected']} | "
            f"{r['stale_injected']}/{r['stale_candidates']} | "
            f"{r['valid_retained']}/{r['valid_candidates']} |"
        )
    (output / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (output / "manifest.json").write_text(
        canonical(
            {
                "contract": "docs/upgrade/OFFLINE-CONTRACT-v1.md",
                "source": "human-authored fixtures",
                "model": None,
                "memory_snapshot": store.snapshot()["snapshot_id"],
                "task_hash": digest(task.model_dump_json()),
                "protocol_mode": "realistic",
                "evidence_layer": "synthetic_offline",
            }
        ),
        encoding="utf-8",
    )
    return summary
