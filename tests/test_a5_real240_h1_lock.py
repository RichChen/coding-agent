from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
if not PYTHON.is_file():
    PYTHON = Path(sys.executable)
LOCK = ROOT / "scripts" / "lock_a5_pilot_preflight.py"


def test_h1_matrix_lock_is_240_and_blocked_without_target_grader(tmp_path: Path):
    output = tmp_path / "h1"
    result = subprocess.run(
        [str(PYTHON), str(LOCK), "--output-dir", str(output)],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["assigned"] == 240
    assert payload["matrix_lock_status"] == "matrix_locked"
    assert payload["status"] == "blocked"
    assert payload["paid"] is False
    assert payload["model_calls"] == 0
    assert payload["real_240_started"] is False
    assert "target_grader_readiness" in payload["blocking_gates"]

    matrix = json.loads((output / "pilot-matrix-lock.json").read_text(encoding="utf-8"))
    assert matrix["assigned"] == 240
    assert matrix["targets"] == 20
    assert matrix["variants"] == ["B0", "B1", "B2", "B3"]
    assert matrix["seeds"] == [42, 43, 44]
    assert matrix["variant_counts"] == {"B0": 60, "B1": 60, "B2": 60, "B3": 60}
    assert matrix["seed_counts"] == {"42": 80, "43": 80, "44": 80}
    assert matrix["b0_injection"] is False
    assert matrix["b1_b3_injection_required"] is True
    b0 = [row for row in matrix["rows"] if row["variant"] == "B0"]
    injected = [row for row in matrix["rows"] if row["variant"] != "B0"]
    assert len(b0) == 60 and all(row["injection_required"] is False for row in b0)
    assert len(injected) == 180 and all(row["injection_required"] is True for row in injected)
    assert len({row["assignment_id"] for row in matrix["rows"]}) == 240

    schema = json.loads((output / "receipt-schema-lock.json").read_text(encoding="utf-8"))
    for field in (
        "assignment_id", "canonical_target_id", "agent_task_id", "variant", "repeat_id",
        "seed", "memory_snapshot_hash", "injection_receipt_refs", "model_binding_hash",
        "grader_receipt_ref", "cleanup_verified",
    ):
        assert field in schema["required_fields"]

    budget = json.loads((output / "pilot-budget-lock.json").read_text(encoding="utf-8"))
    assert budget["pilot_hard_cap"] == "50.000"
    assert budget["pilot_reference_ceiling"] == "46.080"
    assert budget["memory_build_ledger"] == "separate_not_deducted_from_pilot"
    assert budget["paid"] is False

    gates = json.loads((output / "missing-target-gates.json").read_text(encoding="utf-8"))
    assert gates["status"] == "blocked"
    assert gates["real_240_started"] is False
    grader = next(gate for gate in gates["gates"] if gate["id"] == "target_grader_readiness")
    assert grader["status"] == "missing"
    assert grader["awaiting_repo_grader_readiness"] == 20
