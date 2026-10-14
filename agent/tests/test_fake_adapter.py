"""Tests for FakeAdapter."""

from pathlib import Path

import pytest

from reposkill_agent.adapters.fake_adapter import FakeAdapter
from reposkill_agent.core.contracts import PatchSpec, TaskSpec


@pytest.fixture
def sample_workspace(tmp_path: Path) -> Path:
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "main.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_main.py").write_text(
        "from app.main import x\n\ndef test_x():\n    assert x == 1\n",
        encoding="utf-8",
    )
    (tmp_path / "conftest.py").write_text(
        "import sys\nfrom pathlib import Path\nsys.path.insert(0, str(Path(__file__).parent))\n",
        encoding="utf-8",
    )
    return tmp_path


def test_fake_adapter_read_write_and_diff(sample_workspace: Path):
    adapter = FakeAdapter(sample_workspace)
    assert adapter.read_file("app/main.py") == "x = 1\n"

    adapter.apply_patch(PatchSpec(path="app/main.py", content="x = 2\n"))
    assert adapter.read_file("app/main.py") == "x = 2\n"

    diff = adapter.produce_diff()
    assert "app/main.py" in diff
    assert "-x = 1" in diff
    assert "+x = 2" in diff


def test_fake_adapter_inspect_repo(sample_workspace: Path):
    adapter = FakeAdapter(sample_workspace)
    task = TaskSpec(
        id="t1",
        issue="test",
        repo_path=str(sample_workspace),
        test_command="python -m pytest tests/ -q",
    )
    inspection = adapter.inspect_repo(task)
    assert inspection.file_count >= 3
    assert "app" in inspection.top_level_entries


def test_fake_adapter_run_tests(sample_workspace: Path):
    adapter = FakeAdapter(sample_workspace)
    result = adapter.run_tests("python -m pytest tests/ -q")
    assert result.passed
