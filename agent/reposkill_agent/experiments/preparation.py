"""Offline pilot intake. No executor, provider, host import or budget authority.

Parquet is a private preparation input. Selection reads public columns only.
This module deliberately cannot issue a runnable/funded experiment contract.
"""

from __future__ import annotations

import json
import random
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from pydantic import AwareDatetime, Field

from reposkill_agent.eval.public_export import checked_path
from reposkill_agent.experiments.audit import PriceTable, estimate_cost
from reposkill_agent.experiments.contracts import CommonProfile, ExperimentContract, model_hash
from reposkill_agent.protocol.evaluation import EvaluationSpec
from reposkill_agent.protocol.public import (
    Budget,
    Digest,
    PublicTask,
    RepoRef,
    StrictModel,
    canonical,
    digest,
)

REPOSITORIES = (
    "django/django",
    "sympy/sympy",
    "scikit-learn/scikit-learn",
    "pytest-dev/pytest",
    "sphinx-doc/sphinx",
)
CUTOFF = datetime(2020, 1, 1, tzinfo=UTC)
SELECTION_ID = "a5-pilot20-v1"
PUBLIC_COLUMNS = ("repo", "instance_id", "base_commit", "created_at", "problem_statement")


class PublicIssue(StrictModel):
    repo: str = Field(pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
    instance_id: str = Field(pattern=r"^[A-Za-z0-9_.-]+$")
    base_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    created_at: AwareDatetime
    problem_statement: str = Field(min_length=1)

    @property
    def task_id(self) -> str:
        return "a5-task-" + digest(self.instance_id)[:16]


class SourceLock(StrictModel):
    dataset: str
    revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    split: str
    source_url: str
    sha256: Digest
    size_bytes: int = Field(gt=0)
    rows: int = Field(gt=0)
    readme_sha256: Digest
    retrieved_on: str
    license_status: str
    created_at_semantics: str


def public_issue(raw: dict) -> PublicIssue:
    """Only this explicit allowlist may cross from private intake to selector."""
    return PublicIssue(**{key: raw[key] for key in PUBLIC_COLUMNS})


def select_issues(issues: tuple[PublicIssue, ...]) -> tuple[tuple, tuple, list]:
    issues = tuple(PublicIssue.model_validate(i.model_dump()) for i in issues)
    if len({i.instance_id for i in issues}) != len(issues):
        raise ValueError("duplicate_source_instance")
    chosen, historical = [], []
    for repo in REPOSITORIES:
        eligible = [
            i
            for i in issues
            if i.repo == repo and i.created_at >= CUTOFF and len(i.problem_statement) <= 20000
        ]
        ranked = sorted(eligible, key=lambda i: digest(SELECTION_ID + ":" + i.instance_id))
        if len(ranked) < 4:
            raise ValueError("insufficient_public_candidates:" + repo)
        chosen.extend(ranked[:4])
        older = sorted(
            (
                i
                for i in issues
                if i.repo == repo and i.created_at < CUTOFF and len(i.problem_statement) <= 20000
            ),
            key=lambda i: (i.created_at, i.instance_id),
        )
        # Keep a small, deterministic historical pool per repository.  These
        # are only source candidates at preparation time; no trajectory or
        # validation is implied until the harness runs them.
        historical.extend(older[:5])
    if len({(i.repo, i.base_commit) for i in chosen}) != 20:
        raise ValueError("duplicate_selected_base")
    if len({digest(i.problem_statement.strip()) for i in chosen}) != 20:
        raise ValueError("duplicate_selected_issue")
    target_ids = {i.instance_id for i in chosen}
    history_ids = {i.instance_id for i in historical}
    ledger = []
    for issue in sorted(issues, key=lambda i: i.instance_id):
        if issue.instance_id in target_ids:
            reason = "selected_target_candidate"
        elif issue.instance_id in history_ids:
            reason = "historical_source_candidate_not_validated"
        elif issue.repo not in REPOSITORIES:
            reason = "outside_preregistered_repositories"
        elif len(issue.problem_statement) > 20000:
            reason = "public_dto_length_limit"
        elif issue.created_at < CUTOFF:
            reason = "older_than_target_cutoff"
        else:
            reason = "outside_four_per_repo_hash_rank"
        ledger.append(
            {
                "instance_id": issue.instance_id,
                "repo": issue.repo,
                "reason": reason,
                "public_issue_hash": digest(issue.problem_statement),
            }
        )
    return tuple(chosen), tuple(historical), ledger


def make_public_task(issue: PublicIssue) -> PublicTask:
    p = CommonProfile()
    return PublicTask(
        task_id=issue.task_id,
        issue_text=issue.problem_statement,
        repo_ref=RepoRef(repo_id=issue.repo, revision=issue.base_commit, revision_kind="commit"),
        workspace_id=issue.task_id + "-public",
        execution_profile_ref=p.backend,
        allowed_tools=("read", "search", "patch", "public_test"),
        budget=Budget(
            wall_seconds=p.wall_seconds,
            model_calls=p.model_calls,
            input_tokens=p.input_tokens,
            output_tokens=p.output_tokens,
            tool_calls=p.tool_calls,
            retry_limit=p.retry_limit,
        ),
    )


def assignments(tasks: tuple[PublicTask, ...], contract: ExperimentContract) -> list[dict]:
    contract = ExperimentContract.model_validate(contract.model_dump())
    tasks = tuple(PublicTask.model_validate(t.model_dump()) for t in tasks)
    if contract.target_count != 20 or contract.repeats != 3 or len(tasks) != 20:
        raise ValueError("pilot20_assignment_shape")
    if len({t.task_id for t in tasks}) != 20:
        raise ValueError("duplicate_assignment_task")
    p = contract.profile
    for task in tasks:
        if (
            task.execution_profile_ref != p.backend
            or task.allowed_tools != ("read", "search", "patch", "public_test")
            or (
                task.budget.model_calls,
                task.budget.input_tokens,
                task.budget.output_tokens,
                task.budget.tool_calls,
                task.budget.wall_seconds,
                task.budget.retry_limit,
            )
            != (
                p.model_calls,
                p.input_tokens,
                p.output_tokens,
                p.tool_calls,
                p.wall_seconds,
                p.retry_limit,
            )
        ):
            raise ValueError("assignment_runtime_profile_mismatch")
    rows = []
    # Five balanced Latin rotations per repeat: every variant has every position 5 times.
    for repeat, seed in enumerate(contract.seeds):
        rng = random.Random(seed)
        ordered = sorted(tasks, key=lambda t: t.task_id)
        rng.shuffle(ordered)
        variants = list(contract.variants)
        rng.shuffle(variants)
        for n, task in enumerate(ordered):
            order = variants[n % 4 :] + variants[: n % 4]
            for position, variant in enumerate(order):
                rows.append(
                    {
                        "assignment_id": digest(
                            f"{contract.experiment_id}:{task.task_id}:{variant}:{repeat}"
                        ),
                        "experiment_id": contract.experiment_id,
                        "task_id": task.task_id,
                        "public_task_hash": model_hash(task),
                        "variant": variant,
                        "repeat_id": repeat,
                        "organization_seed": seed,
                        "provider_seed": None,
                        "pair_position": position,
                        "sequence": len(rows),
                        "profile_hash": model_hash(contract.profile),
                        "run_attempt": 0,
                        "state": "planned_not_started",
                    }
                )
    return rows


def private_test_list(value: str) -> list[str]:
    parsed = json.loads(value)
    if not isinstance(parsed, list) or not all(isinstance(x, str) and x for x in parsed):
        raise ValueError("invalid_private_test_list")
    return parsed


def readiness(*, selected: int, missing_history: list[str]) -> dict:
    # No boolean or config value can approve a run in this offline preparation tool.
    return {
        "phase": "preparation_only",
        "real_api_enabled": False,
        "pilot_started": False,
        "selected_target_candidates": selected,
        "qualified_runnable_tasks": 0,
        "dataset_frozen_for_execution": False,
        "memory_frozen_for_execution": False,
        "missing_same_repo_history": missing_history,
        "blockers": [
            "explicit_user_A5_budget_approval",
            "final_model_snapshot_and_verified_price",
            "source_license_and_duplicate_review",
            "public_solution_hint_review",
            "pinned_public_seed_and_environment_inventory",
            "historical_trace_validation_and_dependency_mapping",
            "harness_repository_test_grader_preflight",
            "harness_B0_B3_adapter_profile_and_operation_receipts",
            "harness_shared_call_token_tool_retry_and_money_budget_preflight",
        ],
        "automatic_execution": "not_implemented",
    }


def prepare_pilot20(source: Path, lock_path: Path, output: Path) -> dict:
    """Generate a new review bundle from pinned local data, without executing it."""
    checked_path(output.absolute(), "output-check")
    if output.exists():
        raise FileExistsError(output)
    lock = SourceLock.model_validate_json(lock_path.read_text(encoding="utf-8"))
    data = source.read_bytes()
    if len(data) != lock.size_bytes or digest(data) != lock.sha256:
        raise ValueError("source_lock_mismatch")
    if lock.revision not in lock.source_url or "resolve/" + lock.revision not in lock.source_url:
        raise ValueError("source_revision_unpinned")
    import pyarrow as pa
    import pyarrow.parquet as pq

    # Selection never reads solution/test columns; even private-field corruption cannot rank tasks.
    issues = tuple(
        public_issue(r)
        for r in pq.read_table(pa.BufferReader(data), columns=list(PUBLIC_COLUMNS)).to_pylist()
    )
    if len(issues) != lock.rows:
        raise ValueError("source_row_count_mismatch")
    targets, history, ledger = select_issues(issues)
    root = Path(__file__).resolve().parents[2]
    review_file = root / "configs/a5/pilot20-public-review.json"
    review = json.loads(review_file.read_text(encoding="utf-8"))
    if review["source_sha256"] != lock.sha256:
        review = None  # Test/other data cannot inherit the real dataset's review.
    elif set(review["items"]) != {i.instance_id for i in targets}:
        raise ValueError("public_review_selection_mismatch")
    selected_ids = {i.instance_id for i in (*targets, *history)}
    raw_rows = {
        r["instance_id"]: r
        for r in pq.read_table(pa.BufferReader(data)).to_pylist()
        if r["instance_id"] in selected_ids
    }
    tasks = tuple(make_public_task(i) for i in targets)
    contract = ExperimentContract(
        experiment_id="a5-pilot-20-v1",
        mode="pilot_template",
        target_count=20,
        repeats=3,
        seeds=(42, 43, 44),
    )
    schedule = assignments(tasks, contract)
    missing = [r for r in REPOSITORIES if not any(h.repo == r for h in history)]
    ready = readiness(selected=len(targets), missing_history=missing)
    docs: dict[str, object] = {
        "source-lock.json": lock.model_dump(mode="json"),
        "experiment-contract.provisional.json": contract.model_dump(mode="json"),
        "selection-ledger.json": ledger,
        "assignments.json": schedule,
        "readiness.json": ready,
    }
    artifacts: dict[str, bytes] = {}
    if review is not None:
        docs["public-input-review.json"] = review
    inventory, history_inventory = [], []
    for issue, task in zip(targets, tasks, strict=True):
        raw = raw_rows[issue.instance_id]
        prefix = "private/tasks/" + issue.task_id
        f2p, p2p = private_test_list(raw["FAIL_TO_PASS"]), private_test_list(raw["PASS_TO_PASS"])
        if not f2p or not raw["test_patch"] or not raw["patch"]:
            raise ValueError("missing_private_evaluation_material")
        spec = EvaluationSpec(
            task_id=task.task_id,
            hidden_test_refs=(prefix + "/test.patch", prefix + "/benchmark-evaluation.json"),
        )
        docs["public/tasks/" + task.task_id + ".json"] = task.model_dump(mode="json")
        docs[prefix + "/evaluation-spec.json"] = spec.model_dump(mode="json")
        docs[prefix + "/benchmark-evaluation.json"] = {
            "kind": "swe_bench_repository_tests_not_H3_function_probes",
            "task_id": task.task_id,
            "source_instance_id": issue.instance_id,
            "repo": issue.repo,
            "base_commit": issue.base_commit,
            "version": raw["version"],
            "environment_setup_commit": raw["environment_setup_commit"],
            "FAIL_TO_PASS": f2p,
            "PASS_TO_PASS": p2p,
            "test_patch_ref": prefix + "/test.patch",
            "grader_status": "pending_harness",
        }
        artifacts[prefix + "/gold.patch"] = raw["patch"].encode()
        artifacts[prefix + "/test.patch"] = raw["test_patch"].encode()
        # Preserve raw rows privately for reproducibility, never expose hints_text to the model.
        docs[prefix + "/source-row.json"] = raw
        hint = bool(
            re.search(
                r"(?i)\b(code fix|the fix is|propose.{0,25}fix|workaround)\b",
                issue.problem_statement,
            )
        )
        inventory.append(
            {
                "task_id": task.task_id,
                "source_instance_id": issue.instance_id,
                "repo": issue.repo,
                "base_commit": issue.base_commit,
                "pr_created_at": issue.created_at.isoformat(),
                "title": issue.problem_statement.splitlines()[0],
                "public_task_hash": model_hash(task),
                "issue_hash": digest(issue.problem_statement),
                "source_row_hash": digest(canonical(raw)),
                "duplicate_group_provisional": "source-instance:" + issue.instance_id,
                "split_intent": "heldout",
                "reviewed_for_execution": False,
                "preparation_exposure": ["public_issue_metadata_review_only_no_method_tuning"],
                "public_solution_hint_flag": hint,
                "public_solution_hint_review": "see_public_input_review" if review else "pending",
                "public_input_review": review["items"][issue.instance_id] if review else None,
                "source_url": (
                    f"https://github.com/{issue.repo}/pull/{issue.instance_id.rsplit('-', 1)[1]}"
                ),
                "seed_status": "pinned_commit_not_checked_out",
                "license_status": "review_required",
                "environment_status": "pending_harness",
            }
        )
        license_path = source.parent.parent / "licenses" / (task.task_id + ".txt")
        if license_path.is_file():
            content = checked_path(license_path.parent, license_path.name).read_bytes()
            relative = "provenance/licenses/" + task.task_id + ".txt"
            artifacts[relative] = content
            license_name = "COPYING" if issue.repo == "scikit-learn/scikit-learn" else "LICENSE"
            inventory[-1].update(
                license_status="pinned_repo_license_captured; dataset_card_unspecified",
                license_sha256=digest(content),
                license_ref=relative,
                license_source_url=(
                    f"https://raw.githubusercontent.com/{issue.repo}/"
                    f"{issue.base_commit}/{license_name}"
                ),
            )
    for issue in history:
        # Preserve an actual historical issue, not an invented successful agent trajectory.
        docs["history-candidates/" + issue.task_id + "/public-issue.json"] = issue.model_dump(
            mode="json"
        )
        docs["private/history/" + issue.task_id + "/source-row.json"] = raw_rows[issue.instance_id]
        history_inventory.append(
            {
                "source_instance_id": issue.instance_id,
                "repo": issue.repo,
                "base_commit": issue.base_commit,
                "pr_created_at": issue.created_at.isoformat(),
                "public_issue_hash": digest(issue.problem_statement),
                "split_intent": "memory_build",
                "status": "source_candidate_only",
                "validated": False,
                "record": None,
                "reason": "no_observed_historical_agent_trajectory_or_validation; do_not_fabricate",
            }
        )
    docs["candidate-inventory.json"] = inventory
    docs["history-candidate-inventory.json"] = history_inventory
    if review is not None:
        ready["blockers"].remove("public_solution_hint_review")
        ready["public_input_review"] = "completed_with_published_hints_disclosed"
    ready["repo_license_evidence_captured"] = sum("license_sha256" in i for i in inventory)
    docs["public/task-index.json"] = [
        {"task_id": t.task_id, "path": "tasks/" + t.task_id + ".json", "sha256": model_hash(t)}
        for t in tasks
    ]
    dry = estimate_cost(contract)
    reference = PriceTable(
        version="harness-R2-contract-2026-09-21-reference-only",
        currency="USD",
        input_per_million=0.30,
        output_per_million=1.20,
    )
    docs["budget-request.DRAFT.json"] = {
        "approval_status": "awaiting_user_A5_approval",
        "approved_amount": None,
        "other_thread_budget_inherited": False,
        "real_api_enabled": False,
        "proposed_model": "deepseek-flash, thinking disabled; snapshot unbound",
        "proposed_run_cap_usd": 0.04,
        "proposed_total_cap_usd": 10.0,
        "scheduled_runs_cap_sum_usd": 9.6,
        "unallocated_reserve_usd": 0.4,
        "reserve_allows_extra_runs": False,
        "model_snapshot": None,
        "verified_current_price": None,
        "unpriced": ["machine time", "future memory build"],
        "price_evidence": (
            "coding-harness docs/upgrade/R2-EXPERIMENT-CONTRACT.zh-CN.md; reference only"
        ),
        "unpriced_dry_run": dry,
        "illustrative_online_estimate": estimate_cost(contract, reference),
        "rules": [
            "240 first attempts only; model retries already within each 6-call cap",
            "failures stay in the denominator and cost ledger",
            "no paid builder/router/summary/grader in this proposal",
            "reruns, extra preparation model calls or price changes require an updated request",
            "no run before both data/host qualification and explicit user budget approval",
        ],
    }
    docs["host-handoff.json"] = {
        "status": "requirements_only_do_not_execute",
        "source_dataset_revision": lock.revision,
        "task_count": 20,
        "assignment_count": 240,
        "profile": contract.profile.model_dump(),
        "agent_public_fields": list(PublicTask.model_fields),
        "private_material_mount": "grader_only; never mount bundle root or raw parquet",
        "public_tool_semantics": ["read", "search", "patch", "public_test"],
        "required_host_tools": list(contract.profile.tools),
        "pending": {
            "grader": "repository tests with test_patch and F2P/P2P; H3 probes insufficient",
            "seed": "checkout each exact base_commit, inventory/hash, public-only mount",
            "environment": "pin recipe/dependencies/image; original seed must fail independently",
            "history": "freeze reviewed historical traces/MemoryRecords; no target answers",
            "policy": "bind all four variants and same frozen pool; B0 adds no locator/context",
            "usage": "all model starts incl. failures/retry, op/attempt, provider usage and money",
            "injection": "requested hash/range and actual sent bytes linked to model op/attempt",
            "fairness": "same backend/tools/context/model/caps; extra plugin reads must be metered",
            "budget": "aggregate input/output/tool/retry/wall/money preflight; no second client",
        },
    }
    report = {
        "target_candidates": len(targets),
        "history_candidates": len(history),
        "per_repo": dict(Counter(i.repo for i in targets)),
        "planned_task_runs": len(schedule),
        "started_runs": 0,
        "external_model_calls": 0,
        "qualified_runnable_tasks": 0,
        "repair_success": None,
        "missing_same_repo_history": missing,
        "flagged_public_solution_hints": sum(i["public_solution_hint_flag"] for i in inventory),
        "public_input_reviewed": 20 if review else 0,
        "provisional_semantic_groups": len({r["group"] for r in review["items"].values()})
        if review
        else None,
        "repo_license_files": sum("license_sha256" in i for i in inventory),
        "readiness": ready,
        "selection_hash": digest(canonical([i.instance_id for i in targets])),
        "public_tasks_hash": digest(canonical([t.model_dump(mode="json") for t in tasks])),
        "assignments_hash": digest(canonical(schedule)),
    }
    docs["preparation-report.json"] = report
    rows = "\n".join(
        f"| {i['source_instance_id']} | {i['repo']} | {i['public_solution_hint_flag']} |"
        for i in inventory
    )
    artifacts["report.md"] = (
        "# A5 pilot-20 preparation (not executed)\n\n"
        f"20 real issue candidates / 5 repos; {len(history)} historical issue candidates. "
        "240 planned assignments, 0 started runs, 0 model calls. No repair success claim.\n\n"
        "Candidate selection and public DTOs are frozen for review, not approved for execution. "
        "Historical issues are not validated MemoryRecords. Missing history: "
        + ", ".join(missing)
        + ". Public issue hints remain verbatim and are flagged, not silently removed.\n\n"
        "| Source instance | Repo | Public solution hint flag (incomplete heuristic) |\n"
        "|---|---|---|\n" + rows + "\n\n"
        "See public-input-review.json when present for the manual public-issue review. "
        "Captured repository licenses do not supply an absent dataset-card license statement. "
        "Final provenance/cluster freeze and seed/environment qualification remain open. "
        "Repository-test grading requires host work; H3 probes cannot run it. "
        "Private raw rows, solution/test patches and F2P/P2P lists are outside public/. "
        "Never mount the bundle root. No assumption of model pretraining decontamination.\n\n"
        "Budget DRAFT: propose USD 0.04/run, USD 10 overall (unapproved). "
        "At historical reference input/output prices of 0.30/1.20 per million, "
        "the 11.52M/2.88M token ceiling estimates USD 6.912. Current prices/snapshot unbound; "
        "not a bill or permission. Wait for explicit user A5 approval and host/data readiness.\n"
    ).encode()
    for name, value in docs.items():
        artifacts[name] = (canonical(value) + "\n").encode()
    sources = [
        Path(__file__),
        root / "scripts/prepare_a5_pilot20.py",
        review_file,
        lock_path,
        root / "docs/upgrade/A5-PILOT20-PREPARATION.md",
    ]
    artifacts["code-manifest.json"] = (
        canonical(
            {
                p.resolve().relative_to(root).as_posix()
                if p.resolve().is_relative_to(root)
                else p.name: digest(p.read_bytes())
                for p in sources
            }
        )
        + "\n"
    ).encode()
    artifacts["artifact-manifest.json"] = (
        canonical({name: digest(content) for name, content in artifacts.items()}) + "\n"
    ).encode()
    output.mkdir(parents=True, exist_ok=False)
    for name, content in artifacts.items():
        path = checked_path(output, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(content)
    return report
