from pathlib import Path
import hashlib
import json
import subprocess
import sys

from src.eval.a5_memory_snapshot import sha_file

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
if not PYTHON.is_file():
    PYTHON = Path(sys.executable)
S2 = ROOT / "docs" / "upgrade" / "evidence" / "A5-memory-pool-76-s2"
INPUT = S2 / "validated-memory-records.jsonl"
EXPORT = ROOT / "scripts" / "export_a5_memory_snapshot.py"
AUDIT = ROOT / "scripts" / "audit_a5_memory_snapshot.py"


def test_h0_export_and_audit_via_cli(tmp_path: Path):
    before = sha_file(INPUT)
    output = tmp_path / "h0"
    export = subprocess.run(
        [str(PYTHON), str(EXPORT), "--input", str(INPUT), "--output-dir", str(output)],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert export.returncode == 0, export.stdout + export.stderr
    payload = json.loads(export.stdout)
    assert payload["n_records"] == 11
    assert payload["boundary_passed"] is True
    assert payload["model_calls"] == 0
    assert payload["paid"] is False
    assert sha_file(INPUT) == before

    snapshot = output / "memory-snapshot.jsonl"
    manifest = json.loads((output / "memory-snapshot-manifest.json").read_text(encoding="utf-8"))
    rows = [json.loads(line) for line in snapshot.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 11
    assert len({row["source_id"] for row in rows}) == 11
    assert all(row["record_state"] == "validated_lightweight" for row in rows)
    assert all(row["validation_scope"] == "public_independent_smoke_receipt" for row in rows)
    assert all(row["full_grader_validated"] is False for row in rows)
    assert all(row["private_grader_run"] is False for row in rows)
    assert manifest["snapshot_hash"] == hashlib.sha256(snapshot.read_bytes()).hexdigest()
    assert manifest["source_ready_20_of_20"] is False

    failure = json.loads((output / "failure-ledger-ref.json").read_text(encoding="utf-8"))
    assert failure["failed_count"] == 4
    assert failure["blocked_count"] == 5
    assert failure["promoted_failed_or_blocked"] is False

    boundary = json.loads((output / "public-boundary-audit.json").read_text(encoding="utf-8"))
    assert boundary["passed"] is True
    assert boundary["private_marker_hits"] == []

    audit = subprocess.run(
        [str(PYTHON), str(AUDIT), "--snapshot", str(snapshot), "--manifest", str(output / "memory-snapshot-manifest.json")],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert audit.returncode == 0, audit.stdout + audit.stderr
    assert json.loads(audit.stdout)["snapshot_hash"] == manifest["snapshot_hash"]
    assert (S2 / "validated-memory-records.jsonl").read_bytes()  # old evidence still present
    assert sha_file(INPUT) == before
