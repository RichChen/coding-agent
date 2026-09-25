import json
from pathlib import Path

import pytest

from reposkill_agent.memory.cards_v4 import (
    V4_SOURCE_IDS,
    PilotTargetInSources,
    assert_sources_disjoint,
    build_memory_cards_v4,
    select_runs,
    target_ids,
)

CANONICAL = Path("configs/a5/canonical-handoff.json")
TARGETS = set(json.loads(Path("configs/a5/pilot20-harness-consumption-manifest.json").read_text(encoding="utf-8"))["targets"])


def test_v4_sources_are_disjoint_from_pilot_targets():
    assert_sources_disjoint(V4_SOURCE_IDS, target_ids(CANONICAL))
    assert set(V4_SOURCE_IDS).isdisjoint(TARGETS)
    assert len(V4_SOURCE_IDS) == 15


def test_select_smallest_solved_repeat():
    runs = [
        {"source_id": "django__django-10914", "repeat": 2, "solved": True},
        {"source_id": "django__django-10914", "repeat": 1, "solved": False},
        {"source_id": "django__django-10914", "repeat": 3, "solved": True},
        {"source_id": "other-task", "repeat": 1, "solved": True},
    ]
    chosen, ignored = select_runs(runs, ("django__django-10914",), set())
    assert chosen["django__django-10914"]["repeat"] == 2
    assert ignored == ["other-task"]


def test_select_smallest_failed_repeat_when_none_solved():
    runs = [
        {"source_id": "sympy__sympy-12171", "repeat": 3, "solved": False},
        {"source_id": "sympy__sympy-12171", "repeat": 1, "solved": False},
    ]
    chosen, ignored = select_runs(runs, ("sympy__sympy-12171",), set())
    assert chosen["sympy__sympy-12171"]["repeat"] == 1
    assert ignored == []


def test_pilot_target_id_stops_the_build():
    runs = [{"source_id": "django__django-13265", "repeat": 1, "solved": True}]
    with pytest.raises(PilotTargetInSources):
        select_runs(runs, V4_SOURCE_IDS, {"django__django-13265"})


def _pool(source_id: str, repo: str = "demo/demo") -> dict:
    return {
        "canonical_id": source_id,
        "expected_repo": repo,
        "expected_base_commit": "abc123def456",
        "public_task": {},
    }


def _write_canonical(path: Path, targets: list[str], sources: list[str]) -> None:
    path.write_text(
        json.dumps(
            {
                "target_tasks": [{"canonical_id": item} for item in targets],
                "memory_build_source_pool": [_pool(item) for item in sources],
            }
        ),
        encoding="utf-8",
    )


def _write_legacy(root: Path, source_id: str) -> Path:
    run = root / "legacy" / source_id
    (run / "run" / "session" / "artifacts").mkdir(parents=True)
    (run / "run" / "events.jsonl").write_text(
        json.dumps(
            {
                "event_type": "tool.intent",
                "payload": {"name": "run_command", "arguments": {"command": "python -m pytest tests/test_a.py -q"}},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (run / "public-trajectory.json").write_text(
        json.dumps({"issue_summary": "Legacy issue.", "public_evidence": [], "actions": [], "public_verification": "", "failure_notes": []}),
        encoding="utf-8",
    )
    (run / "candidate-delta.json").write_text(json.dumps({"changed": {}}), encoding="utf-8")
    snapshot = root / "snap.jsonl"
    snapshot.write_text(
        json.dumps(
            {
                "source_id": source_id,
                "source_dir": str(run),
                "bindings": {"repo": "demo/demo", "base_revision": "abc123def456"},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return snapshot


def test_missing_sprint_run_uses_legacy_label(tmp_path):
    source_id = "pytest-dev__pytest-5221"
    canonical = tmp_path / "canonical.json"
    _write_canonical(canonical, ["django__django-13265"], [source_id])
    snapshot = _write_legacy(tmp_path, source_id)
    verification = tmp_path / "verify.json"
    verification.write_text(json.dumps({"results": [{"source_id": source_id, "status": "grader_unavailable"}]}), encoding="utf-8")
    saved = list(__import__("reposkill_agent.memory.cards_v4", fromlist=["V4_SOURCE_IDS"]).V4_SOURCE_IDS)
    import reposkill_agent.memory.cards_v4 as cards_v4

    cards_v4.V4_SOURCE_IDS = (source_id,)
    try:
        cards, ignored, missing = build_memory_cards_v4(
            canonical_path=canonical,
            snapshot_path=snapshot,
            verification_path=verification,
            runs=[],
            path_base=tmp_path,
        )
    finally:
        cards_v4.V4_SOURCE_IDS = tuple(saved)
    assert missing == []
    assert ignored == []
    assert cards[0].verification_status == "unverified"
    assert cards[0].label_origin == "legacy_verification"
    assert cards[0].layout == "memory_pool"
