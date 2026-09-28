import asyncio
import json

import pytest

from scripts import run_a5_main
from scripts.run_a5_main import handoff_path_for, out_root_for, resumable, run_phase, write_b0_handoff

TASK = {"id": "django__django-16527", "repo": "django/django", "created_at": "2023-02-05T22:05:00Z"}


def _summary(root, phase, **fields):
    path = root / TASK["id"] / phase / "r1" / "summary.json"
    path.parent.mkdir(parents=True)
    row = {"task_id": TASK["id"], "variant": phase.upper(), "solved": False, "status": "fail", "cost_cny": "0"}
    row.update(fields)
    path.write_text(json.dumps(row), encoding="utf-8")
    return path


def test_mock_and_real_runs_use_separate_roots():
    assert out_root_for(True).name == "a5-main-mock"
    assert out_root_for(False).name == "a5-main"
    assert handoff_path_for(True).name == "main-b0-runs.mock.json"
    assert handoff_path_for(False).name == "main-b0-runs.json"


def test_resume_requires_matching_mock_profile_and_variant():
    good = {"mock": False, "profile": "b0-v2", "variant": "B0"}
    assert resumable(good, phase="b0", mock=False) is None
    assert resumable({"variant": "B0"}, phase="b0", mock=False)
    assert resumable({**good, "mock": True}, phase="b0", mock=False)
    assert resumable({**good, "profile": "b0-v1"}, phase="b0", mock=False)
    assert resumable(good, phase="b2", mock=False)


def test_real_phase_refuses_a_mock_summary(tmp_path, monkeypatch):
    path = _summary(tmp_path, "b0", mock=True, profile="b0-v2")
    before = path.read_bytes()

    async def must_not_run(*args, **kwargs):
        raise AssertionError("a run started over a mock summary")

    monkeypatch.setattr(run_a5_main, "run_task", must_not_run)
    with pytest.raises(SystemExit, match="mock run"):
        asyncio.run(run_phase([TASK], "b0", cards=None, mock=False, repeats=1, out_root=tmp_path))
    assert path.read_bytes() == before


def test_real_phase_refuses_a_summary_without_mock_field(tmp_path, monkeypatch):
    _summary(tmp_path, "b0")

    async def must_not_run(*args, **kwargs):
        raise AssertionError("a run started over an unlabeled summary")

    monkeypatch.setattr(run_a5_main, "run_task", must_not_run)
    with pytest.raises(SystemExit, match="no mock/profile"):
        asyncio.run(run_phase([TASK], "b0", cards=None, mock=False, repeats=1, out_root=tmp_path))


def test_real_phase_skips_a_real_summary(tmp_path, monkeypatch):
    _summary(tmp_path, "b0", mock=False, profile="b0-v2")

    async def must_not_run(*args, **kwargs):
        raise AssertionError("a finished run was repeated")

    monkeypatch.setattr(run_a5_main, "run_task", must_not_run)
    assert asyncio.run(run_phase([TASK], "b0", cards=None, mock=False, repeats=1, out_root=tmp_path)) == []


def test_real_handoff_refuses_a_mock_summary(tmp_path):
    _summary(tmp_path, "b0", mock=True, profile="b0-v2")
    destination = tmp_path / "main-b0-runs.json"
    with pytest.raises(SystemExit, match="mock run"):
        write_b0_handoff(mock=False, out_root=tmp_path, destination=destination, tasks=[TASK])
    assert not destination.exists()


def test_mock_handoff_accepts_mock_summaries(tmp_path):
    _summary(tmp_path, "b0", mock=True, profile="b0-v2")
    destination = tmp_path / "main-b0-runs.mock.json"
    write_b0_handoff(mock=True, out_root=tmp_path, destination=destination, tasks=[TASK])
    payload = json.loads(destination.read_text(encoding="utf-8"))
    assert payload["scope"] == "mock"
    assert [run["source_id"] for run in payload["runs"]] == [TASK["id"]]
