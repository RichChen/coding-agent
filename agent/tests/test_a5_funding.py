import json

import pytest

from reposkill_agent.experiments.funding import FundingContract
from reposkill_agent.protocol.public import digest


def test_funding_contract_exact_cny_partition_and_reference_cost():
    funding = FundingContract.model_validate_json(
        '{"schema_version":"1.1","authorization":"user_approved_approximately_50_CNY_and_necessary_memory_build",'
        '"currency":"CNY","pilot_cap":"50.000","pilot_reference_ceiling":"46.080",'
        '"per_run_cap":"0.192","pilot_runs":240,"memory_build_budget":"separate_user_authorized",'
        '"memory_build_attempt_min":30,"memory_build_attempt_cap":50,"target_validated_records_min":15,'
        '"target_validated_records_max":25,"distinct_history_sources_target":20,"max_attempts_per_source":2,'
        '"input_per_million":"2.000",'
        '"output_per_million":"8.000",'
        '"price_provenance":"user_screenshot_peak_cache_miss_reference_not_provider_verified",'
        '"model_snapshot":null,"verified_price_ref":null,"execution_enabled":false}'
    )
    allocation = funding.allocation()
    assert allocation["pilot_authorized_cap"] == "50.000"
    assert allocation["pilot_reference_ceiling"] == "46.080"
    assert allocation["memory_build_budget"] == "separate_user_authorized"
    assert allocation["host_execution_ready"] is False


def test_funding_contract_rejects_underfunding_or_partition_drift():
    base = FundingContract.model_validate_json(
        open("configs/a5/funding-cny-v1.json", encoding="utf-8").read()
    ).model_dump(mode="json")
    with pytest.raises(ValueError, match="pilot_reference"):
        FundingContract(**{**base, "pilot_reference_ceiling": "50.001"})
    with pytest.raises(ValueError, match="underfunded"):
        FundingContract(**{**base, "per_run_cap": "0.1"})


def test_funded_build_bundle_is_prepared_only_and_private_material_stays_outside_public():
    report = json.loads(
        open(
            "reports/upgrade/a5-funded-build-preparation-20260921-v12/status.json",
            encoding="utf-8",
        ).read()
    )
    assert report["build_source_jobs"] == 20
    assert report["planned_build_attempts"] == 40
    assert report["external_model_calls"] == report["started_runs"] == 0
    assert report["validated_memories"] == 0
    jobs = json.loads(
        open(
            "reports/upgrade/a5-funded-build-preparation-20260921-v12/build-jobs.json",
            encoding="utf-8",
        ).read()
    )
    assert len(jobs) == 20
    assert {j["state"] for j in jobs} == {"prepared_not_started"}
    attempts = json.loads(
        open(
            "reports/upgrade/a5-funded-build-preparation-20260921-v12/build-attempt-plan.json",
            encoding="utf-8",
        ).read()
    )
    assert len(attempts) == 40
    assert {a["state"] for a in attempts} == {"planned_not_started"}
    handoff = json.loads(
        open(
            "reports/upgrade/a5-funded-build-preparation-20260921-v12/harness-build-handoff.json",
            encoding="utf-8",
        ).read()
    )
    assert handoff["execution_enabled"] is False
    assert len(handoff["assignments"]) == 20
    assert all(
        a["base_snapshot"] is None and a["candidate_snapshot"] is None
        for a in handoff["assignments"]
    )
    for path in (
        __import__("pathlib")
        .Path("reports/upgrade/a5-funded-build-preparation-20260921-v1/public")
        .glob("*.json")
    ):
        text = path.read_text(encoding="utf-8")
        assert "gold.patch" not in text and "test_patch" not in text


def test_funded_build_artifacts_are_hashed():
    root = __import__("pathlib").Path("reports/upgrade/a5-funded-build-preparation-20260921-v12")
    manifest = json.loads((root / "artifact-manifest.json").read_text(encoding="utf-8"))
    assert all(digest((root / path).read_bytes()) == value for path, value in manifest.items())
