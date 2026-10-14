import subprocess
import sys
from pathlib import Path


def test_dataset_oracle_script_passes_for_new_tasks():
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "scripts/check_dataset_oracle.py"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "All oracle solutions PASS" in result.stdout
