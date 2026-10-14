from pathlib import Path
import json
import subprocess
import sys

from src.eval.a5_pilot_fixture import (
    expected_kwargs,
    fixture_assignment,
    fixture_bindings,
    make_fixture_receipt,
    mutate,
    run_fail_closed_cases,
)
from src.eval.a5_receipts import validate_pilot_receipt

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
if not PYTHON.is_file():
    PYTHON = Path(sys.executable)
FIXTURE = ROOT / "scripts" / "run_a5_pilot_fixture.py"


def test_h2_fail_closed_rules_without_model():
    result = run_fail_closed_cases()
    assert result["fixture_only"] is True
    assert result["model_calls"] == 0
    assert result["paid"] is False
    assert result["real_240_started"] is False
    assert result["all_ok"] is True
    names = {case["name"] for case in result["cases"]}
    assert "B0_happy" in names and "B3_happy" in names
    assert "B0_has_injection" in names
    assert "missing_grader_receipt" in names
    assert "cleanup_false" in names


def test_h2_cli_marks_fixture_only_and_does_not_claim_pilot(tmp_path: Path):
    output = tmp_path / "h2"
    proc = subprocess.run(
        [str(PYTHON), str(FIXTURE), "--output-dir", str(output)],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["fixture_only"] is True
    assert payload["model_calls"] == 0
    assert payload["paid"] is False
    assert payload["real_240_started"] is False
    assert payload["fail_closed_all_ok"] is True
    ledger = json.loads((output / "fixture-ledger.json").read_text(encoding="utf-8"))
    assert "do not import as pilot-240" in ledger["note"]
    for variant in ("B0", "B1", "B2", "B3"):
        receipt = json.loads((output / "receipts" / variant / "receipt.json").read_text(encoding="utf-8"))
        assert receipt["fixture_only"] is True
        assert receipt["paid"] is False
        assert receipt["model_calls"] == 0
        assert receipt["pilot_claim"] == "not_a_real_pilot"
        if variant == "B0":
            assert receipt["injection_receipt_refs"] == []
        else:
            assert receipt["injection_receipt_refs"]


def test_h2_direct_validator_rejects_b1_without_source_hash():
    bindings = fixture_bindings()
    assignment = fixture_assignment()
    receipt = make_fixture_receipt("B1", bindings=bindings, assignment=assignment)
    receipt["injection_receipt_refs"][0]["source_hash"] = "nope"
    validation = validate_pilot_receipt(receipt, **expected_kwargs({**assignment, "variant": "B1"}, bindings))
    assert validation.valid is False
    assert "injection_binding" in validation.errors
    broken = mutate(make_fixture_receipt("B1", bindings=bindings, assignment=assignment), paid=True)
    assert "fixture_paid" in validate_pilot_receipt(broken, **expected_kwargs({**assignment, "variant": "B1"}, bindings)).errors


def test_pilot_lifecycle_allows_documented_zero_injection_and_blocked_row():
    bindings = fixture_bindings()
    assignment = fixture_assignment()
    receipt = make_fixture_receipt("B3", bindings=bindings, assignment=assignment)
    receipt["injection_receipt_refs"] = []
    receipt["injection_decision"] = "rejected_unknown"
    assert validate_pilot_receipt(receipt).valid
    del receipt["injection_decision"]
    assert "injection_decision_missing" in validate_pilot_receipt(receipt).errors

    blocked = make_fixture_receipt("B1", bindings=bindings, assignment=assignment)
    blocked.update(status="blocked", operation_id=None, attempt_ids=[],
                   injection_receipt_refs=[], usage=None, reservation=None,
                   settlement=None, candidate_hash=None, grader_receipt_ref=None,
                   cleanup_verified=None, failure_reason="contract_baseline_mismatch")
    assert validate_pilot_receipt(blocked).valid
    blocked["attempt_ids"] = ["invented"]
    assert "inactive_has_execution_evidence" in validate_pilot_receipt(blocked).errors
