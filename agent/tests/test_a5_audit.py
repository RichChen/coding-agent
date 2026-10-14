import json

import pytest

from reposkill_agent.experiments.audit import (
    InjectionAudit,
    PriceTable,
    ResultRow,
    UsageAttempt,
    audit_injections,
    cost_ledger,
    estimate_cost,
    summarize,
)
from reposkill_agent.experiments.contracts import (
    DatasetManifest,
    ExperimentContract,
    MemoryBuildManifest,
    model_hash,
)
from reposkill_agent.experiments.offline import fixture_inputs, run_offline
from reposkill_agent.protocol.public import digest
from tests.test_a5_variants import decisions


def usage(**changes):
    return UsageAttempt(
        **{
            "run_id": "r",
            "operation_id": "op",
            "attempt_id": "a",
            "component": "repair",
            "phase": "online",
            "outcome": "failed",
            **changes,
        }
    )


def test_usage_missing_is_unknown_and_extras_are_charged():
    rows = tuple(
        usage(operation_id=name, component=name)
        for name in ("repair", "retry", "router", "summary", "builder", "verifier", "grader")
    )
    ledger = cost_ledger(rows, amortization_targets=12)
    assert ledger["online"]["calls"] == 7
    assert ledger["online"]["unknown_usage_calls"] == 7
    assert ledger["full_cost"] is None
    with pytest.raises(ValueError, match="duplicate_cost"):
        cost_ledger(rows + rows[:1], amortization_targets=12)


def test_full_cost_has_dev_build_and_fixed_unique_target_amortization():
    def charged(phase, amount):
        return usage(
            phase=phase,
            operation_id=phase,
            cost=amount,
            cost_status="provider",
            currency="USD",
            price_version="fixture-price",
        )

    report = cost_ledger(
        tuple(charged(p, v) for p, v in (("online", 3), ("build", 12), ("dev", 2))),
        amortization_targets=12,
    )
    assert report["full_cost"] == 17
    assert report["build_cost_per_unique_target"] == 1
    assert cost_ledger((), amortization_targets=12)["full_cost"] == 0


def test_actual_injection_needs_hash_model_attempt_and_host_evidence():
    decision = decisions()[3]
    c = decision.items[0]
    base = dict(
        run_id="r",
        decision_id=decision.decision_id,
        candidate_id=c.candidate_id,
        stage="prepared_view",
        requested_hash=c.text_hash,
        evidence_ref="host-context",
        reason="host",
    )
    prepared = InjectionAudit(**base)
    result = audit_injections(decision, (prepared,), (), run_id="r")
    assert result["actually_injected"] == 0 and result["unconfirmed"] == 1
    actual = InjectionAudit(
        **{
            **base,
            "stage": "actually_injected",
            "actual_hash": digest(c.text),
            "end_char": len(c.text),
            "operation_id": "op",
            "attempt_id": "a",
        }
    )
    with pytest.raises(ValueError, match="unverified"):
        audit_injections(decision, (actual,), (), run_id="r")
    assert audit_injections(decision, (actual,), (usage(),), run_id="r")["actually_injected"] == 1
    with pytest.raises(ValueError):
        audit_injections(
            decision, (actual.model_copy(update={"actual_hash": "0" * 64}),), (usage(),), run_id="r"
        )


def test_attempt_count_and_pass_cannot_be_invented():
    c, *_ = fixture_inputs()
    row = dict(
        experiment_id=c.experiment_id,
        task_id="x",
        variant="B0",
        repeat_id=0,
        run_id="r",
        profile_hash=model_hash(c.profile),
        outcome="invalid_env",
    )
    with pytest.raises(ValueError, match="unaccounted"):
        ResultRow(**row, model_attempts_started=1)
    with pytest.raises(ValueError, match="unverified"):
        ResultRow(**{**row, "outcome": "pass", "model_attempts_started": 0})
    with pytest.raises(ValueError, match="model_attempts_started"):
        ResultRow(**row)


def heldout_reporting_fixture():
    # A distinct test-only contract; never relabels the actual smoke report/data.
    c, d, m, *_ = fixture_inputs()
    entries = []
    for e in d.entries:
        data = e.model_dump()
        if e.split == "dev":
            data.update(split="heldout", development_exposure=())
        entries.append(data)
    ds = DatasetManifest(**{**d.model_dump(), "entries": entries})
    mm = MemoryBuildManifest(**{**m.model_dump(), "dataset_hash": model_hash(ds)})
    cc = ExperimentContract(
        **{**c.model_dump(), "dataset_hash": model_hash(ds), "memory_hash": model_hash(mm)}
    )
    return cc, ds, mm


def test_missing_invalid_env_failure_and_degraded_stay_in_denominator():
    c, d, m = heldout_reporting_fixture()

    def row(variant, outcome, attempt=0):
        return ResultRow(
            experiment_id=c.experiment_id,
            task_id="a5-dev-0",
            variant=variant,
            repeat_id=0,
            run_id=f"{variant}-{attempt}",
            run_attempt=attempt,
            profile_hash=model_hash(c.profile),
            outcome=outcome,
            model_attempts_started=0,
            collected=1,
            passed=int(outcome == "pass"),
            evaluation_ref="private-result",
            method_degraded=variant == "B3",
        )

    rows = (row("B0", "fail"), row("B0", "pass", 1), row("B1", "invalid_env"), row("B3", "pass"))
    report = summarize(c, d, m, rows)
    assert report["variants"]["B0"]["assigned"] == 4
    assert report["variants"]["B0"]["pass"] == 0
    assert report["variants"]["B0"]["missing"] == 3
    assert report["variants"]["B1"]["invalid_env"] == 1
    assert report["variants"]["B3"]["method_degraded"] == 1
    pairs = [p for p in report["paired_task_differences"] if p["task_id"] == "a5-dev-0"]
    assert [p["paired_success_delta"] for p in pairs] == [0, None, 1]
    assert report["reruns_excluded_from_primary"] == ["B0-1"]
    assert report["costs"]["full_cost"] is None
    assert report["costs"]["missing_primary_rows"] == 13
    with pytest.raises(ValueError, match="duplicate_result"):
        summarize(c, d, m, rows + rows[:1])
    with pytest.raises(ValueError, match="unfair"):
        summarize(c, d, m, (rows[0].model_copy(update={"profile_hash": "0" * 64}),))
    with pytest.raises(ValueError, match="duplicate_run_id"):
        summarize(c, d, m, (rows[0], rows[2].model_copy(update={"run_id": rows[0].run_id})))


@pytest.mark.parametrize(
    "component,phase",
    [("builder", "build"), ("grader", "online"), ("summary", "online"), ("repair", "build")],
)
def test_unrelated_model_attempt_does_not_prove_injection(component, phase):
    decision = decisions()[3]
    candidate = decision.items[0]
    receipt = InjectionAudit(
        run_id="r",
        decision_id=decision.decision_id,
        candidate_id=candidate.candidate_id,
        stage="actually_injected",
        requested_hash=candidate.text_hash,
        actual_hash=candidate.text_hash,
        end_char=len(candidate.text),
        operation_id="op",
        attempt_id="a",
        evidence_ref="host",
        reason="sent",
    )
    with pytest.raises(ValueError, match="unverified_model_injection"):
        audit_injections(
            decision, (receipt,), (usage(component=component, phase=phase),), run_id="r"
        )


def test_partial_receipt_and_host_rejection_are_distinct():
    decision = decisions()[3]
    c = decision.items[0]
    receipt = InjectionAudit(
        run_id="r",
        decision_id=decision.decision_id,
        candidate_id=c.candidate_id,
        stage="actually_injected",
        requested_hash=c.text_hash,
        actual_hash=digest(c.text[2:12]),
        start_char=2,
        end_char=12,
        operation_id="op",
        attempt_id="a",
        evidence_ref="host",
        reason="truncated",
    )
    assert audit_injections(decision, (receipt,), (usage(),), run_id="r")["actually_injected"] == 1
    for changes in ({"run_id": "other"}, {"requested_hash": "0" * 64}, {"attempt_id": "other"}):
        with pytest.raises(ValueError):
            audit_injections(
                decision, (receipt.model_copy(update=changes),), (usage(),), run_id="r"
            )
    with pytest.raises(ValueError, match="duplicate_receipt"):
        audit_injections(decision, (receipt, receipt), (usage(),), run_id="r")
    rejected = receipt.model_copy(
        update={
            "stage": "rejected",
            "actual_hash": None,
            "start_char": 0,
            "end_char": 0,
        }
    )
    assert audit_injections(decision, (rejected,), (), run_id="r")["host_rejected"] == 1
    with pytest.raises(ValueError, match="contradictory"):
        audit_injections(decision, (receipt, rejected), (usage(),), run_id="r")


def test_dev_usage_is_costed_separately_and_missing_build_usage_refused():
    c, d, m, *_ = fixture_inputs()
    row = ResultRow(
        experiment_id=c.experiment_id,
        task_id="a5-dev-0",
        variant="B0",
        repeat_id=0,
        run_id="r",
        profile_hash=model_hash(c.profile),
        outcome="fail",
        model_attempts_started=1,
        usage=(usage(),),
    )
    report = summarize(c, d, m, (row,))
    assert report["costs"]["dev"]["calls"] == 1
    assert report["costs"]["online"]["calls"] == 0
    assert report["costs"]["full_cost"] is None
    data = m.model_dump()
    data["history"][0]["record"]["build_usage"] = {
        "method": "llm",
        "model": "test-only",
        "calls": 1,
        "token_status": "unknown",
    }
    mm = MemoryBuildManifest(**data)
    cc = c.model_copy(update={"memory_hash": model_hash(mm)})
    with pytest.raises(ValueError, match="unaccounted_memory_build"):
        summarize(cc, d, mm, ())
    build = usage(
        run_id="build", phase="build", component="builder", memory_id=mm.history[0].record.memory_id
    )
    assert summarize(cc, d, mm, (), build_dev_usage=(build,))["costs"]["build"]["calls"] == 1


def test_report_refuses_contract_tampering_and_unreviewed_data():
    c, d, m, *_ = fixture_inputs()
    with pytest.raises(ValueError, match="profile_change"):
        summarize(
            c.model_copy(update={"profile": c.profile.model_copy(update={"model_calls": 7})}),
            d,
            m,
            (),
        )
    entries = (d.entries[0].model_copy(update={"reviewed": False}), *d.entries[1:])
    with pytest.raises(ValueError, match="missing_contamination_review"):
        summarize(c, d.model_copy(update={"entries": entries}), m, ())


def test_dry_run_shape_and_unknown_price():
    for n, runs, calls in ((12, 144, 864), (20, 240, 1440)):
        c = ExperimentContract(
            experiment_id="pilot",
            mode="pilot_template",
            target_count=n,
            repeats=3,
            seeds=(42, 43, 44),
        )
        result = estimate_cost(c)
        assert result["task_runs"] == runs and result["online_call_limit"] == calls
        assert result["full_cost_estimate"] is None and not result["real_api_enabled"]
        priced = estimate_cost(
            c,
            PriceTable(
                version="example", currency="USD", input_per_million=1, output_per_million=2
            ),
        )
        assert priced["full_cost_estimate"] == (runs * 48000 + runs * 12000 * 2) / 1e6


def test_offline_bundle_four_smokes_no_main_denominator_no_private_leak(tmp_path):
    directory = tmp_path / "offline"
    report = run_offline(directory)
    assert report["smoke_scenarios"] == 4 and report["decision_rows"] == 16
    assert report["external_model_calls"] == 0 and report["repair_success"] is None
    assert report["dev_rows_excluded"] == 16
    assert all(
        v["assigned"] == 0 and v["success_rate"] is None for v in report["variants"].values()
    )
    hashes = json.loads((directory / "artifact-manifest.json").read_text())
    for relative, sha in hashes.items():
        assert digest((directory / relative).read_bytes()) == sha
    for relative in ("public-tasks.json", "public-index.json", "decisions.json"):
        assert "A5_PRIVATE_SENTINEL" not in (directory / relative).read_text()
    with pytest.raises(FileExistsError):
        run_offline(directory)
