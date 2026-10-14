"""Authorized budget arithmetic and private-side build handoff, never an executor."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from reposkill_agent.eval.public_export import checked_path
from reposkill_agent.experiments.contracts import CommonProfile, model_hash
from reposkill_agent.experiments.preparation import (
    make_public_task,
    private_test_list,
    public_issue,
)
from reposkill_agent.protocol.evaluation import EvaluationSpec
from reposkill_agent.protocol.public import PublicTask, Versioned, canonical, digest, safe_relative

Money = Decimal
HISTORY_PER_REPO = 5
BUILD_ATTEMPTS_PER_SOURCE = 2


class FundingContract(Versioned):
    authorization: Literal["user_approved_approximately_50_CNY_and_necessary_memory_build"]
    currency: Literal["CNY"] = "CNY"
    # The pilot has a user-approved ceiling of about 50 CNY.  The reference
    # token arithmetic is lower (46.080 CNY) and leaves operational headroom.
    pilot_cap: Money = Field(gt=0, le=50, allow_inf_nan=False)
    pilot_reference_ceiling: Money = Field(gt=0, allow_inf_nan=False)
    per_run_cap: Money = Field(gt=0, allow_inf_nan=False)
    pilot_runs: Literal[240] = 240
    memory_build_budget: Literal["separate_user_authorized"]
    memory_build_attempt_min: Literal[30] = 30
    memory_build_attempt_cap: Literal[50] = 50
    target_validated_records_min: Literal[15] = 15
    target_validated_records_max: Literal[25] = 25
    distinct_history_sources_target: Literal[20] = 20
    max_attempts_per_source: Literal[2] = 2
    input_per_million: Money = Field(gt=0, allow_inf_nan=False)
    output_per_million: Money = Field(gt=0, allow_inf_nan=False)
    price_provenance: Literal["user_screenshot_peak_cache_miss_reference_not_provider_verified"]
    model_snapshot: None = None
    verified_price_ref: None = None
    execution_enabled: Literal[False] = False

    @model_validator(mode="after")
    def balanced(self):
        if self.pilot_reference_ceiling > self.pilot_cap:
            raise ValueError("pilot_reference_exceeds_cap")
        p = CommonProfile()
        cost = (
            p.input_tokens * self.input_per_million + p.output_tokens * self.output_per_million
        ) / Decimal(1000000)
        if self.per_run_cap < cost:
            raise ValueError("underfunded_reference_token_budget")
        if self.pilot_runs * self.per_run_cap > self.pilot_cap:
            raise ValueError("pilot_exceeds_allocation")
        if self.memory_build_attempt_min > self.memory_build_attempt_cap:
            raise ValueError("memory_attempt_range_invalid")
        return self

    def allocation(self) -> dict:
        # Revalidate model_copy callers, with exact Decimal computation.
        c = FundingContract.model_validate(self.model_dump())
        return {
            "currency": c.currency,
            "pilot_authorized_cap": str(c.pilot_cap),
            "pilot_reference_ceiling": str(c.pilot_reference_ceiling),
            "pilot_headroom": str(c.pilot_cap - c.pilot_reference_ceiling),
            "memory_build_budget": c.memory_build_budget,
            "memory_build_attempt_range": [c.memory_build_attempt_min, c.memory_build_attempt_cap],
            "target_validated_record_range": [
                c.target_validated_records_min,
                c.target_validated_records_max,
            ],
            "actual_spent": None,
            "spend_status": "pilot_and_memory_build_ledgers_separate; no_host_usage_imported",
            "budget_authorized": True,
            "host_execution_ready": False,
        }


def prepare_funded_build(bundle: Path, funding_file: Path, output: Path) -> dict:
    """Turn the four locked historical candidates into isolated host build jobs."""
    checked_path(output.absolute(), "funded-output")
    if output.exists():
        raise FileExistsError(output)
    funding = FundingContract.model_validate_json(funding_file.read_text(encoding="utf-8"))
    manifest = json.loads(checked_path(bundle, "artifact-manifest.json").read_text())

    def read(name):
        safe_relative(name)
        data = checked_path(bundle, name).read_bytes()
        if name not in manifest or digest(data) != manifest[name]:
            raise ValueError("preparation_artifact_mismatch")
        return json.loads(data)

    targets = read("candidate-inventory.json")
    history = read("history-candidate-inventory.json")
    if len(targets) != 20 or len({t["source_instance_id"] for t in targets}) != 20:
        raise ValueError("target_inventory_shape")
    if len(history) != 20 or len({h["source_instance_id"] for h in history}) != 20:
        raise ValueError("build_source_set_changed")
    target_ids = {t["source_instance_id"] for t in targets}
    target_bases = {(t["repo"], t["base_commit"]) for t in targets}
    target_issues = {t["issue_hash"] for t in targets}
    docs, jobs, attempts = {}, [], []
    for h in history:
        source_id = h["source_instance_id"]
        h = next(h for h in history if h["source_instance_id"] == source_id)
        original_id = "a5-task-" + digest(source_id)[:16]
        raw = read("private/history/" + original_id + "/source-row.json")
        issue = public_issue(raw)
        if (
            issue.instance_id != source_id
            or issue.repo != h["repo"]
            or issue.base_commit != h["base_commit"]
            or digest(issue.problem_statement) != h["public_issue_hash"]
        ):
            raise ValueError("history_inventory_mismatch")
        if (
            source_id in target_ids
            or (issue.repo, issue.base_commit) in target_bases
            or digest(issue.problem_statement) in target_issues
            or issue.created_at.year >= 2020
        ):
            raise ValueError("target_or_nonhistorical_build_source")
        base_task = make_public_task(issue)
        task = PublicTask.model_validate(
            {
                **base_task.model_dump(),
                "task_id": "a5-build-" + digest(source_id)[:16],
                "workspace_id": "a5-build-" + digest(source_id)[:16] + "-public",
                "budget": {
                    **base_task.budget.model_dump(),
                    "max_cost": float(funding.per_run_cap),
                    "currency": "CNY",
                },
            }
        )
        prefix = "private/" + task.task_id
        spec = EvaluationSpec(
            task_id=task.task_id, hidden_test_refs=(prefix + "/repository-evaluation.json",)
        )
        f2p, p2p = private_test_list(raw["FAIL_TO_PASS"]), private_test_list(raw["PASS_TO_PASS"])
        if not f2p or not raw["test_patch"]:
            raise ValueError("missing_build_grader_material")
        docs["public/" + task.task_id + ".json"] = task.model_dump(mode="json")
        docs[prefix + "/evaluation-spec.json"] = spec.model_dump(mode="json")
        docs[prefix + "/repository-evaluation.json"] = {
            "task_id": task.task_id,
            "repo": issue.repo,
            "base_commit": issue.base_commit,
            "environment_setup_commit": raw["environment_setup_commit"],
            "version": raw["version"],
            "test_patch": raw["test_patch"],
            "FAIL_TO_PASS": f2p,
            "PASS_TO_PASS": p2p,
            "access": "independent_grader_only; not_public_validation_evidence",
        }
        job = {
                "job_id": digest("a5-build-wave1:" + source_id),
                "task_id": task.task_id,
                "source_instance_id": source_id,
                "repo": issue.repo,
                "base_commit": issue.base_commit,
                "public_task_hash": model_hash(task),
                "source_row_hash": digest(canonical(raw)),
                "historical_source_at": issue.created_at.isoformat(),
                "trajectory_observed_at": None,
                "validation_checked_at": None,
                "state": "prepared_not_started",
                "run_attempt": 0,
                "context": "none",
                "augmentation": "B0",
                "memory_input": "empty",
                "phase": "build",
                "component": "repair",
                "currency": "CNY",
                "run_cap": str(funding.per_run_cap),
                "profile_hash": model_hash(CommonProfile()),
                "max_attempts": funding.max_attempts_per_source,
                "attempts_reserved": funding.max_attempts_per_source,
            }
        jobs.append(job)
        for attempt in range(1, funding.max_attempts_per_source + 1):
            attempts.append({
                "attempt_id": digest(job["job_id"] + f":attempt:{attempt}"),
                "job_id": job["job_id"],
                "source_instance_id": source_id,
                "attempt": attempt,
                "state": "planned_not_started",
                "retry_of": (
                    None
                    if attempt == 1
                    else digest(job["job_id"] + f":attempt:{attempt - 1}")
                ),
                "failure_retained": True,
                "charged_even_if_failed": True,
            })
    result = {
        "budget_authorized": True,
        "currency": "CNY",
        "pilot_cap": str(funding.pilot_cap),
        "memory_build_budget": funding.memory_build_budget,
        "build_source_jobs": len(jobs),
        "planned_build_attempts": len(attempts),
        "external_model_calls": 0,
        "started_runs": 0,
        "validated_memories": 0,
        "automatic_execution": False,
        "remaining_gates": [
            "harness_repository_grader_and_base_failure_preflight",
            "host_model_snapshot_and_current_price_binding",
            "host_global_CNY_ledger_and_per_stage_caps",
            "source_public_seed_and_semantic_duplicate_review",
            "public_trajectory_validation_dependency_and_receipt_import",
            "separate_historical_source_time_from_actual_replay_time",
            "Sphinx_historical_source_missing_under_frozen_rule",
        ],
    }
    docs.update(
        {
            "funding-contract.json": funding.model_dump(mode="json"),
            "allocation.json": funding.allocation(),
            "build-jobs.json": jobs,
            "status.json": result,
            "host-handoff.json": {
                "budget_approval": "already_given; do_not_reuse_old_awaiting_approval_flag",
                "execution": "after_host_preflight_only; no_direct_model_client",
            "build_wave": "twenty_fixed_source_tasks_with_two_reserved_attempts_each",
                "source_bundle_manifest_hash": digest(canonical(manifest)),
                "holdout_mount": "forbidden; do_not_mount_source_bundle_root_or_parquet",
                "retention": "retain_every_failed/invalid_env/unknown_attempt_and_cost",
                "unknown_cost": "keep_reserved_until_reconciled; never_treat_as_zero",
            "budget_precision": "decimal CNY for pilot; memory build uses a separate host ledger",
                "history_promotion": [
                    "actual_public_observations/actions/hash_and_run/op/attempt_bindings",
                    "public_validation_artifact_and_independent_grader_result_kept_separate",
                    "rule_extraction_candidate_then_review_dependencies_and_provenance",
                    "private_grader_text_and_gold_patch_never_indexed",
                    "actual_build_timestamp_not_backdated_to_historical_PR_timestamp",
                    "all_failed_builds_charged_even_if_no_MemoryRecord_produced",
                    "identical_B1_raw_pool_and_B2_B3_record_sources_frozen_before_pilot",
                ],
            },
        }
    )
    docs["build-attempt-plan.json"] = attempts
    docs["harness-build-handoff.json"] = {
        "schema_version": "1.0",
        "mode": "host_only_handoff",
        "execution_enabled": False,
        "runner": "coding-harness/scripts/run_repo_grader.py",
        "preflight_required": True,
        "private_spec_never_exposed_to_agent": True,
        "assignments": [
            {
                "job_id": job["job_id"],
                "task_id": job["task_id"],
                "public_task": f"public/{job['task_id']}.json",
                "private_evaluation_spec": f"private/{job['task_id']}/evaluation-spec.json",
                "source_evaluation": f"private/{job['task_id']}/repository-evaluation.json",
                "base_snapshot": None,
                "candidate_snapshot": None,
                "status": "awaiting_repo_grader_readiness",
                "phase": "build",
                "component": "repair",
            }
            for job in jobs
        ],
        "receipt_import_required": [
            "operation_id",
            "attempt_id",
            "usage_receipt",
            "candidate_snapshot_hash",
            "independent_grader_artifact",
            "cleanup_status",
        ],
    }
    artifacts = {p: (canonical(v) + "\n").encode() for p, v in docs.items()}
    root = Path(__file__).resolve().parents[2]
    artifacts["code-manifest.json"] = (
        canonical(
            {
                p.relative_to(root).as_posix(): digest(p.read_bytes())
                for p in (
                    Path(__file__),
                    root / "scripts/prepare_a5_funded_build.py",
                    root / "configs/a5/funding-cny-v1.json",
                    root / "docs/upgrade/A5-FUNDED-BUILD-v1.md",
                )
            }
        )
        + "\n"
    ).encode()
    artifacts["artifact-manifest.json"] = (
        canonical({p: digest(v) for p, v in artifacts.items()}) + "\n"
    ).encode()
    output.mkdir(parents=True, exist_ok=False)
    for name, data in artifacts.items():
        path = checked_path(output, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(data)
    return result
