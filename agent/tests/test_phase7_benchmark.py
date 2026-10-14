"""Phase 7 medium benchmark sanity checks."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from reposkill_agent.eval.task_spec import load_tasks
from reposkill_agent.memory.matching import DOMAIN_TAGS
from reposkill_agent.skills.domain import TASK_DOMAIN_TAGS

ROOT = Path(__file__).parent.parent
TASKS_PATH_24 = ROOT / "benchmarks" / "tasks" / "phase7_medium_24.yaml"
TASKS_PATH_48 = ROOT / "benchmarks" / "tasks" / "phase7_medium_48.yaml"
BENCHMARKS_ROOT = ROOT / "benchmarks"


@pytest.fixture(scope="module")
def phase7_catalog():
    if not TASKS_PATH_24.exists():
        pytest.skip("phase7_medium_24.yaml not found")
    return load_tasks(TASKS_PATH_24, benchmarks_root=BENCHMARKS_ROOT)


@pytest.fixture(scope="module")
def phase7_medium48_catalog():
    if not TASKS_PATH_48.exists():
        pytest.skip("phase7_medium_48.yaml not found")
    return load_tasks(TASKS_PATH_48, benchmarks_root=BENCHMARKS_ROOT)


def test_phase7_task_count(phase7_catalog):
    assert len(phase7_catalog.tasks) == 24


def test_phase7_repos_exist(phase7_catalog):
    repos = {Path(t.repo_path).name for t in phase7_catalog.tasks}
    assert repos == {
        "medium_inventory",
        "medium_config_loader",
        "medium_event_pipeline",
    }


@pytest.mark.parametrize(
    "repo_name",
    ["medium_inventory", "medium_config_loader", "medium_event_pipeline"],
)
def test_medium_repo_pytest_collects(repo_name: str):
    repo = BENCHMARKS_ROOT / "repos" / repo_name
    proc = subprocess.run(
        ["python", "-m", "pytest", "tests/", "--collect-only", "-q"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "test session starts" in proc.stdout.lower() or "tests/" in proc.stdout


def test_phase7_tasks_fail_in_broken_state(phase7_catalog):
    """Each task's targeted tests must fail before any agent fix (no saturation)."""
    failed = 0
    for task in phase7_catalog.tasks:
        repo = Path(task.repo_path)
        proc = subprocess.run(
            task.test_command,
            shell=True,
            cwd=repo,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            failed += 1
    assert failed == len(phase7_catalog.tasks), (
        f"expected all {len(phase7_catalog.tasks)} tasks to fail in broken state, "
        f"but {len(phase7_catalog.tasks) - failed} passed"
    )


def test_phase7_category_coverage(phase7_catalog):
    categories = {
        "context_heavy",
        "skill_heavy",
        "memory_heavy",
        "multi_file_api",
        "traceback_repair",
        "repo_convention",
    }
    found: set[str] = set()
    for task in phase7_catalog.tasks:
        found.update(task.tags)
    for cat in categories:
        assert cat in found, f"missing category tag: {cat}"


def test_phase7_medium48_task_count(phase7_medium48_catalog):
    assert len(phase7_medium48_catalog.tasks) == 48


def test_phase7_medium48_repos_exist(phase7_medium48_catalog):
    repos = {Path(t.repo_path).name for t in phase7_medium48_catalog.tasks}
    assert repos == {
        "medium_inventory",
        "medium_config_loader",
        "medium_event_pipeline",
        "medium_auth_rules",
    }


def test_phase7_medium48_domain_tags_in_registry(phase7_medium48_catalog):
    assert TASK_DOMAIN_TAGS == DOMAIN_TAGS
    for task in phase7_medium48_catalog.tasks:
        for tag in task.tags:
            if tag in TASK_DOMAIN_TAGS:
                assert tag in DOMAIN_TAGS


def test_medium_auth_rules_pytest_collects():
    repo = BENCHMARKS_ROOT / "repos" / "medium_auth_rules"
    proc = subprocess.run(
        ["python", "-m", "pytest", "tests/", "--collect-only", "-q"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "test session starts" in proc.stdout.lower() or "tests/" in proc.stdout


def test_phase7_medium48_tasks_fail_in_broken_state(phase7_medium48_catalog):
    """Each task's targeted tests must fail before any agent fix (no saturation)."""
    failed = 0
    for task in phase7_medium48_catalog.tasks:
        repo = Path(task.repo_path)
        proc = subprocess.run(
            task.test_command,
            shell=True,
            cwd=repo,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            failed += 1
    assert failed == len(phase7_medium48_catalog.tasks), (
        f"expected all {len(phase7_medium48_catalog.tasks)} tasks to fail in broken state, "
        f"but {len(phase7_medium48_catalog.tasks) - failed} passed"
    )


def test_phase7_medium48_category_coverage(phase7_medium48_catalog):
    categories = {
        "context_heavy",
        "skill_heavy",
        "memory_heavy",
        "multi_file_api",
        "traceback_repair",
        "repo_convention",
        "auth",
    }
    found: set[str] = set()
    for task in phase7_medium48_catalog.tasks:
        found.update(task.tags)
    for cat in categories:
        assert cat in found, f"missing category tag: {cat}"
