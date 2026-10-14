import json

import pytest

from scripts import calibrate_a5_image_grader as calibration


IMAGE = "coding-harness-test@sha256:" + "a" * 64
NODEID = "tests/test_target.py::test_target"


def positive_evidence(image=IMAGE):
    phases = ("setup", "call", "teardown")
    return {
        "image": image,
        "cleanup_verified": True,
        "execution": {"status": "succeeded", "exit_code": 0},
        "receipt": {
            "schema": "repo.pytest.receipt.v1",
            "complete": True,
            "exit_code": 0,
            "collected": [NODEID],
            "collection_errors": [],
            "reports": [
                {"nodeid": NODEID, "when": phase, "outcome": "passed", "wasxfail": None}
                for phase in phases
            ],
        },
    }


def make_row(tmp_path, *, image=IMAGE):
    receipt_path = tmp_path / "known-good.json"
    receipt_path.write_text(json.dumps(positive_evidence(image)), encoding="utf-8")
    return {
        "task_id": "pytest-dev__pytest-1234",
        "repo": "pytest-dev/pytest",
        "base_revision": "b" * 40,
        "status": "baseline_ready",
        "known_good_image_digest": image,
        "known_good_receipt_ref": str(receipt_path),
        "grader": {"known_good": "pass", "known_good_outcomes": {NODEID: "passed"}},
    }


def test_known_good_receipt_is_bound_to_image_and_exact_outcomes(tmp_path):
    row = make_row(tmp_path)
    binding = calibration._known_good_binding(row)
    assert binding["status"] == "pass"
    assert binding["receipt_sha256"]
    assert binding["verified_outcomes"] == {NODEID: "passed"}

    row["known_good_image_digest"] = "other@sha256:" + "b" * 64
    assert calibration._known_good_binding(row)["reason"] == "known_good_receipt_binding_or_outcome_mismatch"


def test_known_good_binding_reads_legacy_isolation_image(tmp_path):
    row = make_row(tmp_path)
    receipt_path = tmp_path / "known-good.json"
    evidence = positive_evidence()
    evidence.pop("image")
    evidence["isolation"] = {"Config": {"Image": IMAGE}}
    receipt_path.write_text(json.dumps(evidence), encoding="utf-8")

    binding = calibration._known_good_binding(row)

    assert binding["status"] == "pass"
    assert binding["receipt_image"] == IMAGE


def test_known_good_binding_uses_frozen_baseline_failures_when_outcome_map_is_absent(tmp_path):
    row = make_row(tmp_path)
    row["grader"].pop("known_good_outcomes")
    row["actual_baseline_failed"] = [NODEID]
    binding = calibration._known_good_binding(row)
    assert binding["status"] == "pass"
    assert binding["expected_outcomes"] == {NODEID: "passed"}


def test_known_good_receipt_missing_or_not_passing_fails_closed(tmp_path):
    row = make_row(tmp_path)
    row["known_good_receipt_ref"] = str(tmp_path / "missing.json")
    assert calibration._known_good_binding(row)["reason"] == "known_good_receipt_unreadable"

    row = make_row(tmp_path)
    row["grader"]["known_good_outcomes"][NODEID] = "failed"
    assert calibration._known_good_binding(row)["reason"] == "known_good_receipt_binding_or_outcome_mismatch"


def test_pilot_binding_checks_repo_and_exact_base_commit():
    target = {
        "expected_repo": "pytest-dev/pytest",
        "target_base_commit": "b" * 40,
        "target_base_hash": "c" * 64,
    }
    row = {"task_id": "pytest-dev__pytest-1234", "repo": "pytest-dev/pytest", "base_revision": "b" * 40}
    assert calibration._validate_pilot_binding(row, {row["task_id"]: target})["status"] == "pass"
    row["base_revision"] = "d" * 40
    assert calibration._validate_pilot_binding(row, {row["task_id"]: target})["reason"] == "pilot_repo_or_base_commit_mismatch"


def test_pilot_lock_rejects_conflicting_target_identities(tmp_path):
    path = tmp_path / "pilot.json"
    path.write_text(json.dumps({"rows": [
        {"canonical_target_id": "target", "expected_repo": "org/repo", "target_base_commit": "a", "target_base_hash": "1"},
        {"canonical_target_id": "target", "expected_repo": "org/repo", "target_base_commit": "b", "target_base_hash": "2"},
    ]}), encoding="utf-8")
    with pytest.raises(ValueError, match="conflicting identity"):
        calibration.pilot_rows_from_lock(path)


@pytest.mark.asyncio
async def test_negative_checks_execute_repository_grader_policy():
    result = await calibration.run_negative_checks(IMAGE)
    assert result["scope"] == "executed_host_policy_fixture_not_target_specific"
    assert result["passed"] is True
    assert [row["case"] for row in result["checks"]] == [
        "protected_path_change", "missing_receipt", "input_integrity_change"
    ]
    assert all(row["status"] == "rejected" for row in result["checks"])


@pytest.mark.asyncio
async def test_calibration_readiness_requires_bound_positive_and_collection(monkeypatch, tmp_path):
    row = make_row(tmp_path)
    out = tmp_path / "task"
    out.mkdir()

    async def fake_run_pytest(image, args, output, **kwargs):
        output.mkdir(parents=True)
        evidence = {
            "cleanup_verified": True,
            "execution": {"status": "succeeded", "exit_code": 0},
            "receipt": {
                "complete": True,
                "exit_code": 0,
                "collection_errors": [],
                "collected": ["tests/test_a.py::test_a", "tests/test_b.py::test_b"],
            },
        }
        (output / "evidence.json").write_text(json.dumps(evidence), encoding="utf-8")
        return evidence

    monkeypatch.setattr(calibration, "run_pytest", fake_run_pytest)
    result = await calibration.calibrate(
        row,
        out,
        pilot_rows={row["task_id"]: {
            "expected_repo": row["repo"],
            "target_base_commit": row["base_revision"],
            "target_base_hash": "c" * 64,
        }},
    )
    assert result["status"] == "ready"
    assert result["grader_ready"] is True
    assert result["canonical_binding_required"] is True
    assert result["negative_checks"]["passed"] is True


@pytest.mark.asyncio
async def test_calibration_blocks_when_known_good_or_target_binding_is_missing(tmp_path):
    row = make_row(tmp_path)
    row["known_good_receipt_ref"] = str(tmp_path / "absent.json")
    out = tmp_path / "blocked"
    out.mkdir()
    result = await calibration.calibrate(row, out)
    assert result["status"] == "blocked"
    assert result["grader_ready"] is False
    assert result["reason"] == "known_good_receipt_unreadable"
    assert not (out / "full-repo").exists()


@pytest.mark.asyncio
async def test_non_ready_input_stays_in_denominator_without_execution(monkeypatch, tmp_path):
    row = make_row(tmp_path)
    row.update({"status": "baseline_mismatch", "reason": "f2p_contract_mismatch"})
    out = tmp_path / "blocked"
    out.mkdir()

    async def unexpected_run(*args, **kwargs):
        raise AssertionError("non-ready input must not start Docker")

    monkeypatch.setattr(calibration, "run_pytest", unexpected_run)
    result = await calibration.calibrate(row, out)

    assert result["status"] == "blocked"
    assert result["reason"] == "input_baseline_status_not_ready"
    assert result["input_baseline_status"] == "baseline_mismatch"
    assert result["input_blocker"] == "f2p_contract_mismatch"
    assert result["full_collection_status"] == "not_run"
    assert not (out / "full-repo").exists()


def test_selected_tasks_cannot_silently_disappear_and_keep_not_ready_rows():
    rows = [{"task_id": "one", "status": "baseline_ready"}]
    with pytest.raises(ValueError, match="missing from input"):
        calibration.select_rows(rows, ["absent"])
    selected = calibration.select_rows([{**rows[0], "status": "baseline_mismatch"}], ["one"])
    assert selected == [{"task_id": "one", "status": "baseline_mismatch"}]
