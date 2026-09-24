"""Host-result analysis only: no grader, runtime, model call or budget authority."""

from __future__ import annotations

from itertools import product
from typing import Literal

from pydantic import Field, model_validator

from reposkill_agent.experiments.contracts import (
    DatasetManifest,
    ExperimentContract,
    MemoryBuildManifest,
    Variant,
    require_frozen,
)
from reposkill_agent.experiments.variants import VariantDecision
from reposkill_agent.protocol.public import Digest, StrictModel, digest


class UsageAttempt(StrictModel):
    run_id: str
    operation_id: str
    attempt_id: str
    component: Literal["repair", "retry", "router", "summary", "builder", "verifier", "grader"]
    phase: Literal["online", "build", "dev"]
    outcome: Literal["succeeded", "failed", "unknown"]
    usage_status: Literal["provider", "estimated", "unknown"] = "unknown"
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    cost: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    cost_status: Literal["provider", "estimated", "unknown"] = "unknown"
    currency: str | None = None
    price_version: str | None = None
    memory_id: str | None = None

    @model_validator(mode="after")
    def complete(self):
        if not all((self.run_id, self.operation_id, self.attempt_id)):
            raise ValueError("missing_usage_identity")
        known = self.input_tokens is not None and self.output_tokens is not None
        if (self.usage_status != "unknown") != known:
            raise ValueError("inconsistent_usage_status")
        if self.usage_status == "unknown" and (
            self.input_tokens is not None or self.output_tokens is not None
        ):
            raise ValueError("partial_usage_must_remain_unknown")
        if (self.cost_status == "unknown") != (self.cost is None):
            raise ValueError("inconsistent_cost_status")
        if self.cost is not None and (not self.currency or not self.price_version):
            raise ValueError("missing_cost_provenance")
        return self


class InjectionAudit(StrictModel):
    run_id: str
    decision_id: str
    candidate_id: str
    stage: Literal["prepared_view", "actually_injected", "rejected"]
    requested_hash: Digest
    actual_hash: Digest | None = None
    start_char: int = Field(default=0, ge=0)
    end_char: int = Field(default=0, ge=0)
    operation_id: str | None = None
    attempt_id: str | None = None
    evidence_ref: str
    reason: str


def audit_injections(
    decision: VariantDecision,
    receipts: tuple[InjectionAudit, ...],
    usage: tuple[UsageAttempt, ...],
    *,
    run_id: str,
) -> dict:
    receipts = tuple(InjectionAudit.model_validate(r.model_dump()) for r in receipts)
    usage = tuple(UsageAttempt.model_validate(u.model_dump()) for u in usage)
    candidates = {c.candidate_id: c for c in decision.items if c.requested}
    attempts = {
        (u.run_id, u.operation_id, u.attempt_id)
        for u in usage
        if u.component in ("repair", "retry") and u.phase in ("online", "dev")
    }
    actual, rejected, prepared, seen = set(), set(), set(), set()
    for r in receipts:
        candidate = candidates.get(r.candidate_id)
        key = (r.candidate_id, r.stage, r.operation_id, r.attempt_id)
        if (
            key in seen
            or candidate is None
            or r.run_id != run_id
            or (r.decision_id != decision.decision_id or r.requested_hash != candidate.text_hash)
            or not r.evidence_ref
        ):
            raise ValueError("unbound_or_duplicate_receipt")
        seen.add(key)
        if r.stage == "actually_injected":
            text = candidate.text[r.start_char : r.end_char]
            if (run_id, r.operation_id, r.attempt_id) not in attempts or (
                not text or r.end_char > len(candidate.text) or digest(text) != r.actual_hash
            ):
                raise ValueError("unverified_model_injection")
            actual.add(r.candidate_id)
        elif r.stage == "rejected":
            if r.actual_hash is not None or r.start_char or r.end_char:
                raise ValueError("rejected_receipt_has_content")
            rejected.add(r.candidate_id)
        else:
            prepared.add(r.candidate_id)
    if actual & rejected:
        raise ValueError("contradictory_receipts")
    return {
        "selected": len(candidates),
        "requested": len(candidates),
        "actually_injected": len(actual),
        "host_rejected": len(rejected),
        "selection_rejected": sum(c.rejected for c in decision.items),
        "prepared_view": len(prepared),
        "unconfirmed": len(candidates.keys() - actual - rejected),
        "observed_following": "unknown",
    }


class ResultRow(StrictModel):
    experiment_id: str
    task_id: str
    variant: Variant
    repeat_id: int = Field(ge=0)
    run_id: str
    run_attempt: int = Field(default=0, ge=0)
    profile_hash: Digest
    outcome: Literal["pass", "fail", "partial", "invalid_env", "not_run"]
    collected: int = Field(default=0, ge=0)
    passed: int = Field(default=0, ge=0)
    evaluation_ref: str | None = None
    failure_reason: str | None = None
    method_degraded: bool = False
    model_attempts_started: int = Field(ge=0)
    usage: tuple[UsageAttempt, ...] = ()

    @model_validator(mode="after")
    def evidence(self):
        if self.passed > self.collected or (
            self.outcome == "pass"
            and (not self.collected or self.passed != self.collected or not self.evaluation_ref)
        ):
            raise ValueError("unverified_evaluation")
        if not self.run_id:
            raise ValueError("missing_run_identity")
        if any(u.run_id != self.run_id or u.phase not in ("online", "dev") for u in self.usage):
            raise ValueError("unbound_online_usage")
        if len({(u.operation_id, u.attempt_id) for u in self.usage}) != len(self.usage):
            raise ValueError("duplicate_model_attempt")
        if self.model_attempts_started != len(self.usage):
            raise ValueError("unaccounted_model_attempt")
        return self


def cost_ledger(attempts: tuple[UsageAttempt, ...], *, amortization_targets: int) -> dict:
    attempts = tuple(UsageAttempt.model_validate(u.model_dump()) for u in attempts)
    if amortization_targets < 1:
        raise ValueError("invalid_amortization_denominator")
    ids = [(u.run_id, u.operation_id, u.attempt_id) for u in attempts]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate_cost_attempt")
    currencies = {u.currency for u in attempts if u.cost is not None}
    if len(currencies) > 1:
        raise ValueError("mixed_currencies")
    result = {}
    for phase in ("online", "build", "dev"):
        rows = [u for u in attempts if u.phase == phase]
        unknown = sum(u.cost is None for u in rows)
        result[phase] = {
            "calls": len(rows),
            "unknown_usage_calls": sum(u.usage_status == "unknown" for u in rows),
            "known_cost_subtotal": sum(u.cost for u in rows if u.cost is not None),
            "cost": None if unknown else sum(u.cost for u in rows),
            "unknown_cost_calls": unknown,
            "cost_status": "unknown"
            if unknown
            else "estimated"
            if any(u.cost_status == "estimated" for u in rows)
            else "provider"
            if rows
            else "no_model_call",
        }
    amounts = [result[p]["cost"] for p in ("online", "build", "dev")]
    result["full_cost"] = None if any(v is None for v in amounts) else sum(amounts)
    build = result["build"]["cost"]
    result["build_cost_per_unique_target"] = None if build is None else build / amortization_targets
    result["amortization_targets"] = amortization_targets
    result["currency"] = next(iter(currencies), None)
    result["scope"] = "all_supplied_model_attempts; excludes unpriced machine and human costs"
    return result


class PriceTable(StrictModel):
    version: str
    currency: str
    input_per_million: float = Field(ge=0, allow_inf_nan=False)
    output_per_million: float = Field(ge=0, allow_inf_nan=False)
    kind: Literal["illustrative", "provider_verified"] = "illustrative"


def estimate_cost(
    contract: ExperimentContract,
    price: PriceTable | None = None,
    *,
    build_input_tokens: int = 0,
    build_output_tokens: int = 0,
    build_calls: int = 0,
) -> dict:
    contract = ExperimentContract.model_validate(contract.model_dump())
    if min(build_calls, build_input_tokens, build_output_tokens) < 0:
        raise ValueError("negative_build_budget")
    runs = contract.target_count * contract.repeats * len(contract.variants)
    inp, out = runs * contract.profile.input_tokens, runs * contract.profile.output_tokens
    online = (
        None
        if price is None
        else (inp * price.input_per_million + out * price.output_per_million) / 1e6
    )
    build = (
        None
        if price is None
        else (
            build_input_tokens * price.input_per_million
            + build_output_tokens * price.output_per_million
        )
        / 1e6
    )
    return {
        "kind": "dry_run_upper_bound_not_actual_cost",
        "real_api_enabled": False,
        "task_runs": runs,
        "online_call_limit": runs * contract.profile.model_calls,
        "input_token_limit": inp,
        "output_token_limit": out,
        "build_call_limit": build_calls,
        "online_cost_estimate": online,
        "build_cost_estimate": build,
        "full_cost_estimate": None if online is None else online + build,
        "build_cost_per_unique_target": None if build is None else build / contract.target_count,
        "price": price.model_dump() if price else None,
        "formula": f"{inp / 1e6:g}*P_in + {out / 1e6:g}*P_out",
        "not_included": "machine rental, missing provider billing categories, dev costs",
    }


def summarize(
    contract: ExperimentContract,
    dataset: DatasetManifest,
    memory: MemoryBuildManifest,
    rows: tuple[ResultRow, ...],
    *,
    build_dev_usage: tuple[UsageAttempt, ...] = (),
) -> dict:
    from reposkill_agent.experiments.contracts import model_hash

    require_frozen(contract, dataset, memory)
    rows = tuple(ResultRow.model_validate(r.model_dump()) for r in rows)
    targets = [e.task_id for e in dataset.entries if e.split == "heldout"]
    assigned = set(product(targets, contract.variants, range(contract.repeats)))
    if contract.mode == "pilot_template" and len(targets) != contract.target_count:
        raise ValueError("pilot_dataset_not_frozen")
    seen, run_ids, first, reruns = set(), set(), {}, []
    usage_rows = []
    for row in rows:
        key = (row.task_id, row.variant, row.repeat_id)
        identity = (*key, row.run_attempt)
        if row.experiment_id != contract.experiment_id or row.profile_hash != model_hash(
            contract.profile
        ):
            raise ValueError("unfair_runtime_profile")
        if identity in seen:
            raise ValueError("duplicate_result")
        seen.add(identity)
        if row.run_id in run_ids:
            raise ValueError("duplicate_run_id")
        run_ids.add(row.run_id)
        entry = next((e for e in dataset.entries if e.task_id == row.task_id), None)
        if entry is None or entry.split == "memory_build" or row.repeat_id >= contract.repeats:
            raise ValueError("unassigned_result")
        phase = "dev" if entry.split == "dev" else "online"
        if phase == "online" and any(u.phase != "online" for u in row.usage):
            raise ValueError("heldout_usage_must_be_online")
        usage_rows.extend(u.model_copy(update={"phase": phase}) for u in row.usage)
        if key not in assigned:
            continue  # dev results are retained below, never in the main denominator
        if row.run_attempt:
            reruns.append(row.run_id)
        else:
            first[key] = row
    results = {}
    for variant in contract.variants:
        keys = [key for key in assigned if key[1] == variant]
        observed = [first[k] for k in keys if k in first]
        passed = sum(r.outcome == "pass" for r in observed)
        results[variant] = {
            "assigned": len(keys),
            "pass": passed,
            "success_rate": passed / len(keys) if keys else None,
            "invalid_env": sum(r.outcome == "invalid_env" for r in observed),
            "fail": sum(r.outcome == "fail" for r in observed),
            "partial": sum(r.outcome == "partial" for r in observed),
            "not_run": sum(r.outcome == "not_run" for r in observed),
            "missing": len(keys) - len(observed),
            "method_degraded": sum(r.method_degraded for r in observed),
        }
    paired = []
    for target in targets:
        for variant in ("B1", "B2", "B3"):
            pairs = [
                (first.get((target, "B0", n)), first.get((target, variant, n)))
                for n in range(contract.repeats)
            ]
            complete = all(
                a is not None
                and b is not None
                and a.outcome != "not_run"
                and b.outcome != "not_run"
                for a, b in pairs
            )
            paired.append(
                {
                    "task_id": target,
                    "variant": variant,
                    "complete": complete,
                    "paired_success_delta": sum(
                        int(b.outcome == "pass") - int(a.outcome == "pass") for a, b in pairs
                    )
                    / contract.repeats
                    if complete
                    else None,
                }
            )
    build_dev_usage = tuple(UsageAttempt.model_validate(u.model_dump()) for u in build_dev_usage)
    if any(u.phase == "online" or u.run_id in run_ids for u in build_dev_usage):
        raise ValueError("unbound_supplemental_usage")
    for h in memory.history:
        recorded = sum(
            u.phase == "build" and u.component == "builder" and u.memory_id == h.record.memory_id
            for u in build_dev_usage
        )
        if recorded != h.record.build_usage.calls:
            raise ValueError("unaccounted_memory_build_attempt")
    usage = tuple(usage_rows) + build_dev_usage
    costs = cost_ledger(usage, amortization_targets=contract.target_count)
    missing_rows = len(assigned - first.keys())
    costs["missing_primary_rows"] = missing_rows
    costs["coverage"] = "incomplete_missing_runs" if missing_rows else "supplied_run_inventory"
    if missing_rows:
        # No receipt is not evidence of no model call for an absent result row.
        costs["full_cost"] = None
        costs["online"]["cost"] = None
        costs["online"]["cost_status"] = "unknown"
    return {
        "protocol": "E-A1",
        "variants": results,
        "paired_task_differences": paired,
        "reruns_excluded_from_primary": reruns,
        "rows": [r.model_dump(mode="json") for r in rows],
        "costs": costs,
        "interpretation": "offline_plumbing_only"
        if contract.mode == "offline_smoke"
        else "descriptive_only",
        "dev_rows_excluded": sum(r.task_id not in targets for r in rows),
    }
