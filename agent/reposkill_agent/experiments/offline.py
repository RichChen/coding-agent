"""Four synthetic dev smoke scenarios. No model, tool or repair execution."""

from __future__ import annotations

import json
import platform
import time
from datetime import UTC, datetime
from pathlib import Path

from reposkill_agent.eval.public_export import checked_path
from reposkill_agent.evidence.models import EvidenceState
from reposkill_agent.experiments.audit import ResultRow, audit_injections, estimate_cost, summarize
from reposkill_agent.experiments.contracts import (
    CommonProfile,
    DataEntry,
    DatasetManifest,
    ExperimentContract,
    HistoryItem,
    MemoryBuildManifest,
    model_hash,
    pilot_blockers,
    validate_manifests,
)
from reposkill_agent.experiments.variants import select_variant
from reposkill_agent.memory.builder import PublicTrajectory
from reposkill_agent.memory.records import (
    BuildUsage,
    Dependency,
    MemoryRecord,
    SourceRef,
    ValidationEvidence,
)
from reposkill_agent.memory.source_manifest import SourcePolicy
from reposkill_agent.memory.validity import Fact, RepoFacts
from reposkill_agent.protocol.public import (
    ArtifactRef,
    Budget,
    PublicTask,
    RepoRef,
    canonical,
    digest,
)

PAST = datetime(2026, 9, 1, tzinfo=UTC)
NOW = datetime(2026, 9, 21, tzinfo=UTC)
SCENARIOS = ("empty", "valid", "known_stale", "unknown")


def fixture_inputs():
    started = time.perf_counter()
    profile = CommonProfile()
    tasks, facts, entries = [], [], []
    public_files = {}
    for n, case in enumerate(SCENARIOS):
        arguments = "text, strict=False" if case == "known_stale" else "text"
        code = f"def parse_config({arguments}):\n    return {{}}\n"
        revision = digest(code)
        public_files[f"task-{n}/parser.py"] = code
        issue = (
            f"parse_config needs investigation for public example {n + 1}; "
            "empty config parsing should preserve its documented behavior."
        )
        task = PublicTask(
            task_id=f"a5-dev-{n}",
            issue_text=issue,
            repo_ref=RepoRef(repo_id="synthetic-parser", revision=revision),
            workspace_id=f"a5-public-{n}",
            allowed_tools=("read", "search", "patch", "public_test"),
            execution_profile_ref=profile.backend,
            budget=Budget(
                model_calls=profile.model_calls,
                input_tokens=profile.input_tokens,
                output_tokens=profile.output_tokens,
                wall_seconds=profile.wall_seconds,
                tool_calls=profile.tool_calls,
                retry_limit=profile.retry_limit,
            ),
        )
        tasks.append(task)
        facts.append(
            RepoFacts(
                repo_id="synthetic-parser",
                revision=revision,
                observed_at=NOW,
                facts=()
                if case == "unknown"
                else (
                    Fact(
                        kind="api_signature",
                        key="parse_config",
                        value="(text,strict=False)" if case == "known_stale" else "(text)",
                        evidence_ref=f"public-code-{n}",
                        repo_revision=revision,
                    ),
                ),
            )
        )
        entries.append(
            DataEntry(
                task_id=task.task_id,
                repo_id=task.repo_ref.repo_id,
                revision=revision,
                source_type="synthetic",
                origin="local:A5 dev fixture",
                license="MIT",
                split="dev",
                occurred_at=NOW,
                time_basis="synthetic_version_order",
                artifact_hash=digest(issue + code),
                duplicate_group="dev-parser-family",
                public_task_hash=model_hash(task),
                public_issue_hash=digest(issue),
                development_exposure=("authored_for_contract_testing",),
                review_evidence="A5-PLAN synthetic materials reviewed; not natural holdout",
                reviewed=True,
            )
        )
    raw = PublicTrajectory(
        issue_summary="Historical parse_config empty config investigation",
        public_evidence=("Public signature was parse_config(text).",),
        actions=(
            "Inspect parser inputs before editing; reproduce empty config with public tests.",
        ),
        public_verification="Run the public parser check at the recorded revision.",
        failure_notes=("Changing unrelated serializer did not help.",),
    ).model_dump_json()
    src_art = ArtifactRef(
        logical_id="historical-trajectory",
        sha256=digest(raw),
        size_bytes=len(raw.encode()),
        run_id="a5-build-fixture",
        relative_path="history/trajectory.json",
    )
    verification_text = (
        "Synthetic public validation fixture: signature parse_config(text); 1 passed."
    )
    val_art = ArtifactRef(
        logical_id="historical-validation",
        sha256=digest(verification_text),
        size_bytes=len(verification_text.encode()),
        run_id="a5-build-fixture",
        relative_path="history/validation.txt",
    )
    source = SourceRef(
        task_id="a5-build-0",
        run_id="a5-build-fixture",
        repo_id="synthetic-parser",
        repo_revision="synthetic-historical-v1",
        protocol_mode="realistic",
        split="memory_build",
        occurred_at=PAST,
        artifact=src_art,
        duplicate_group="historical-inspection-procedure",
    )
    entries.append(
        DataEntry(
            task_id=source.task_id,
            repo_id=source.repo_id,
            revision=source.repo_revision,
            source_type="synthetic",
            origin="local:A5 authored historical fixture",
            license="MIT",
            split="memory_build",
            occurred_at=PAST,
            time_basis="synthetic_version_order",
            artifact_hash=digest(raw),
            duplicate_group=source.duplicate_group,
            development_exposure=("human_authored",),
            review_evidence="Reviewed generic investigation procedure; no target patch/answers",
            reviewed=True,
        )
    )
    dataset = DatasetManifest(
        dataset_id="a5-synthetic-dev-v1",
        entries=tuple(entries),
        contamination_statement=(
            "Manual synthetic split by provenance groups; not natural chronology or pretraining "
            "decontamination. Four dev scenarios never enter main results."
        ),
    )
    procedure = (
        "Inspect parse_config inputs; reproduce empty config with public tests before editing."
    )
    record = MemoryRecord(
        memory_id="a5-parser-procedure",
        kind="procedure",
        status="validated",
        content_hash=digest(procedure),
        procedure=procedure,
        applicability=("parse_config(text) and empty config",),
        verification_recipe="Run the public parser check at this code revision.",
        source_repo_id=source.repo_id,
        sources=(source,),
        created_at=PAST,
        build_usage=BuildUsage(method="human-authored", cost=0, currency="USD"),
        dependencies=(
            Dependency(
                kind="api_signature",
                key="parse_config",
                expected="(text)",
                evidence_ref=src_art.logical_id,
            ),
        ),
        dependency_mapping_complete=True,
        validation=(
            ValidationEvidence(
                artifact=val_art,
                repo_id=source.repo_id,
                repo_revision=source.repo_revision,
                checked_at=PAST,
                collected=1,
                passed=1,
                outcome="pass",
            ),
        ),
        last_validated_at=PAST,
    )
    policy = SourcePolicy(
        allowed_sources=(source,),
        allowed_validation_artifacts=(val_art,),
        target_task_ids=tuple(t.task_id for t in tasks),
        cutoff=NOW,
        excluded_artifact_hashes=tuple(e.artifact_hash for e in entries if e.split == "dev"),
        excluded_duplicate_groups=("dev-parser-family",),
    )
    memory = MemoryBuildManifest(
        build_id="a5-frozen-history-v1",
        dataset_hash=model_hash(dataset),
        policy=policy,
        history=(HistoryItem(source=source, raw_text=raw, record=record),),
        build_wall_ms=(time.perf_counter() - started) * 1000,
    )
    empty_policy = SourcePolicy(**{**policy.model_dump(), "allowed_sources": ()})
    empty = MemoryBuildManifest(
        build_id="a5-empty-control-v1",
        dataset_hash=model_hash(dataset),
        policy=empty_policy,
        history=(),
        build_wall_ms=0,
    )
    contract = ExperimentContract(
        experiment_id="a5-offline-v1",
        mode="offline_smoke",
        target_count=4,
        dataset_hash=model_hash(dataset),
        memory_hash=model_hash(memory),
    )
    validate_manifests(dataset, memory)
    return (
        contract,
        dataset,
        memory,
        empty,
        tasks,
        facts,
        {
            "history/trajectory.json": raw,
            "history/validation.txt": verification_text,
            **{f"public-workspaces/{p}": text for p, text in public_files.items()},
        },
    )


def run_offline(output: Path) -> dict:
    for parent in (output, *output.parents):
        if parent.exists():
            checked_path(parent, "a5-output-check")
    start = time.perf_counter()
    contract, dataset, memory, empty, tasks, facts, artifacts = fixture_inputs()
    decisions, rows, audits = [], [], []
    snapshots = {}
    private_checks = {"empty": 0, "valid": 1, "known_stale": 0, "unknown": 0}
    for case, task, repo_facts in zip(SCENARIOS, tasks, facts, strict=True):
        pool = empty if case == "empty" else memory
        bound = ExperimentContract(**{**contract.model_dump(), "memory_hash": model_hash(pool)})
        snapshots[task.task_id] = model_hash(pool)
        for variant in contract.variants:
            run_id = f"fixture-{task.task_id}-{variant}"
            decision = select_variant(
                task,
                EvidenceState(repo_revision=task.repo_ref.revision),
                repo_facts,
                bound,
                dataset,
                pool,
                variant,
                now=NOW,
                decision_id=run_id,
            )
            if variant == "B3":
                assert sum(c.selected for c in decision.items) == private_checks[case]
            audits.append(audit_injections(decision, (), (), run_id=run_id))
            decisions.append(decision.model_dump(mode="json"))
            rows.append(
                ResultRow(
                    experiment_id=contract.experiment_id,
                    task_id=task.task_id,
                    variant=variant,
                    repeat_id=0,
                    run_id=run_id,
                    profile_hash=model_hash(contract.profile),
                    outcome="not_run",
                    model_attempts_started=0,
                    failure_reason="offline_decision_only_no_repair_or_grader",
                )
            )
    report = summarize(contract, dataset, memory, tuple(rows))
    report.update(
        smoke_scenarios=4,
        decision_rows=len(decisions),
        external_model_calls=0,
        actual_model_injection=False,
        repair_success=None,
        injection_audits=audits,
        local_wall_ms=(time.perf_counter() - start) * 1000,
        build_wall_ms=memory.build_wall_ms,
        machine_cost=None,
        machine_cost_status="not_priced",
        python=platform.python_version(),
    )
    documents = {
        "experiment-contract.json": contract.model_dump(mode="json"),
        "dataset-manifest.json": dataset.model_dump(mode="json"),
        "memory-build-manifest.json": memory.model_dump(mode="json"),
        "empty-memory-manifest.json": empty.model_dump(mode="json"),
        "frozen-task-snapshots.json": snapshots,
        "public-tasks.json": [t.model_dump(mode="json") for t in tasks],
        "public-facts.json": [f.model_dump(mode="json") for f in facts],
        "public-index.json": [
            {"source_hash": h.source.artifact.sha256, "text": h.raw_text} for h in memory.history
        ],
        "decisions.json": decisions,
        "results.json": report,
        "usage.json": [],
        "private/smoke-checks.json": {
            "canary": "A5_PRIVATE_SENTINEL",
            "b3_selected": private_checks,
        },
    }
    for count in (12, 20):
        pilot = ExperimentContract.model_validate_json(
            (Path(__file__).resolve().parents[2] / f"configs/a5/pilot-{count}.json").read_text(
                encoding="utf-8"
            )
        )
        documents[f"pilot-{count}.json"] = {
            "contract": pilot.model_dump(mode="json"),
            "readiness": pilot_blockers(pilot),
            "dataset_status": "unassigned_no_real_heldout_claim",
            "estimator": estimate_cost(pilot),
        }
    for path, value in documents.items():
        artifacts[path] = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    artifacts["report.md"] = (
        "# A5 offline dev smoke\n\n"
        "Four synthetic dev scenarios, 16 B0–B3 decisions. No repair, grader or model run.\n"
        "Main assigned denominator: 0. Repair success: null. External model calls: 0.\n"
        "Actually injected: 0; selected candidates await host model receipts.\n\n"
        "| Scenario | B0 selected | B1 | B2 | B3 |\n|---|---:|---:|---:|---:|\n"
        + "".join(
            "| "
            + case
            + " | "
            + " | ".join(
                str(sum(x["selected"] for x in d["items"])) for d in decisions[n * 4 : n * 4 + 4]
            )
            + " |\n"
            for n, case in enumerate(SCENARIOS)
        )
        + "\nThe historical record and its validation are authored fixtures, not measured repair "
        "evidence. Dev tasks are excluded from the main denominator. B1 uses lexical set "
        "overlap, not BM25. B2/B3 use the same procedure text; B3 additionally checks validity.\n\n"
        "Pilot templates are disabled: 12×4×3 = 144 runs / ≤864 model calls; "
        "20×4×3 = 240 runs / ≤1440 calls. Online price formulas: "
        "6.912×P_in + 1.728×P_out and 11.52×P_in + 2.88×P_out (per million tokens). "
        "Real heldout tasks, model snapshot, verified pricing and monetary caps are unbound.\n\n"
        "Model cost here is zero; machine/human cost is unpriced. This is infrastructure "
        "verification and makes no performance or statistical claim. Public exports and private "
        "smoke assertions are separate. Do not mount this bundle root as an agent workspace.\n"
    )
    root = Path(__file__).resolve().parents[2]
    sources = [
        *Path(__file__).parent.glob("*.py"),
        root / "scripts/run_a5_offline.py",
        *sorted((root / "configs/a5").glob("*.json")),
    ]
    artifacts["code-manifest.json"] = canonical(
        {p.relative_to(root).as_posix(): digest(p.read_bytes()) for p in sources}
    )
    artifacts["artifact-manifest.json"] = canonical({p: digest(v) for p, v in artifacts.items()})
    output.mkdir(parents=True, exist_ok=False)
    for relative, content in artifacts.items():
        destination = output / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
    return report
