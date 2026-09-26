"""Build v4 memory cards from sprint runs, falling back to the legacy pool.

Trajectory choice is fixed: smallest solved repeat, else smallest unsolved
repeat, else the legacy memory-pool trajectory. Card text is never hand-edited.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from reposkill_agent.memory.cards_v3 import (
    NONE_RUN,
    _approach,
    _dependencies,
    _files,
    _pitfalls,
    _test_commands,
)
from reposkill_agent.memory.event_extract import extract_source
from reposkill_agent.memory.records import MemoryCard
from reposkill_agent.memory.source_verification import load_source_verification

V4_SOURCE_IDS = (
    "django__django-10914",
    "django__django-10924",
    "django__django-11039",
    "sympy__sympy-11400",
    "sympy__sympy-12171",
    "scikit-learn__scikit-learn-10297",
    "scikit-learn__scikit-learn-10949",
    "scikit-learn__scikit-learn-11040",
    "scikit-learn__scikit-learn-11281",
    "pytest-dev__pytest-5103",
    "pytest-dev__pytest-5221",
    "sympy__sympy-11870",
    "sympy__sympy-11897",
    "pytest-dev__pytest-5227",
    "scikit-learn__scikit-learn-10508",
)

HANDOFF_SCHEMA = "sprint4.memory-source-runs.v1"
MANIFEST_SCHEMA = "memory-cards.v4.manifest"
FINAL_PROFILE = "b0-v2"


class PilotTargetInSources(RuntimeError):
    """A memory-source run uses a pilot target id. Stop and report."""


def target_ids(handoff_path: Path) -> set[str]:
    data = json.loads(handoff_path.read_text(encoding="utf-8"))
    return {item["canonical_id"] for item in data["target_tasks"]}


def assert_sources_disjoint(source_ids: tuple[str, ...], targets: set[str]) -> None:
    overlap = sorted(set(source_ids) & targets)
    if overlap:
        raise PilotTargetInSources(overlap)


def load_handoff(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != HANDOFF_SCHEMA:
        raise ValueError("unexpected_memory_source_runs_schema")
    if data.get("profile_tag") != FINAL_PROFILE:
        raise ValueError("unexpected_profile_tag")
    runs = data.get("runs") or []
    if not isinstance(runs, list):
        raise ValueError("memory_source_runs_not_a_list")
    return data


def load_handoff_runs(path: Path) -> list[dict]:
    return load_handoff(path)["runs"]


def assert_clean_runs(runs: list[dict], targets: set[str]) -> None:
    leaked = sorted({run["source_id"] for run in runs if run["source_id"] in targets})
    if leaked:
        raise PilotTargetInSources(leaked)
    bad = [
        run["source_id"]
        for run in runs
        if run.get("answer_isolation_pass") is not True or not run.get("clean_image_digest")
    ]
    if bad:
        raise ValueError("isolation_or_digest_missing")


def interim_runs(sprint_root: Path) -> list[dict]:
    runs = []
    for child in sorted(path for path in sprint_root.iterdir() if path.is_dir()):
        grader_path = child / "grader-result.json"
        if not grader_path.is_file():
            continue
        grader = json.loads(grader_path.read_text(encoding="utf-8"))
        solved = bool(grader.get("solved"))
        runs.append(
            {
                "source_id": child.name,
                "repeat": 1,
                "run_dir": str(child),
                "layout": "sprint",
                "solved": solved,
                "grader_status": grader.get("status") or grader.get("grader_status") or "",
            }
        )
    return runs


def select_runs(
    runs: list[dict],
    source_ids: tuple[str, ...],
    targets: set[str],
) -> tuple[dict[str, dict | None], list[str]]:
    leaked = sorted({run["source_id"] for run in runs if run["source_id"] in targets})
    if leaked:
        raise PilotTargetInSources(leaked)
    ignored = sorted({run["source_id"] for run in runs if run["source_id"] not in source_ids})
    chosen: dict[str, dict | None] = {}
    for source_id in source_ids:
        mine = [run for run in runs if run["source_id"] == source_id]
        solved = [run for run in mine if run.get("solved")]
        pool = solved or mine
        if not pool:
            chosen[source_id] = None
            continue
        best = min(pool, key=lambda run: int(run["repeat"]))
        chosen[source_id] = best
    return chosen, ignored


def _pool_index(canonical_path: Path) -> dict[str, dict]:
    data = json.loads(canonical_path.read_text(encoding="utf-8"))
    return {item["canonical_id"]: item for item in data["memory_build_source_pool"]}


def _issue_text(pool_entry: dict, path_base: Path) -> str:
    public = pool_entry.get("public_task") or {}
    rel = public.get("path")
    if not rel:
        return ""
    path = path_base / rel
    if not path.is_file():
        return ""
    payload = json.loads(path.read_text(encoding="utf-8"))
    return str(payload.get("issue_text") or "").strip()


def _legacy_rows(snapshot_path: Path) -> dict[str, dict]:
    rows = {}
    for line in snapshot_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            rows[row["source_id"]] = row
    return rows


def _card_from_run(
    source_id: str,
    *,
    repo: str,
    created_at: str,
    version: str,
    issue: str,
    run_dir: Path,
    layout: str,
    status: str,
    origin: str,
    source_run: str,
    legacy_trajectory: dict | None = None,
) -> MemoryCard:
    extracted = extract_source(run_dir, source_id, layout=layout)
    if not extracted.events_found:
        raise FileNotFoundError(f"events_missing:{source_id}")
    commands = _test_commands(extracted.commands)
    trajectory = legacy_trajectory or {}
    notes = tuple(str(item) for item in trajectory.get("failure_notes") or ())
    return MemoryCard(
        repo=repo,
        created_at=created_at,
        version=version,
        source_id=source_id,
        issue_summary=issue or source_id,
        relevant_files=_files(extracted),
        test_commands=commands[:4] or (NONE_RUN,),
        env_pitfalls=_pitfalls(extracted, commands),
        fix_approach=_approach(extracted, extracted.changed_symbols),
        verification_status=status,  # type: ignore[arg-type]
        dependencies=_dependencies(extracted),
        distillation="rule",
        label_origin=origin,  # type: ignore[arg-type]
        source_run=source_run,
        layout=layout,  # type: ignore[arg-type]
        observations=tuple(str(item) for item in trajectory.get("public_evidence") or ()),
        actions=tuple(str(item) for item in trajectory.get("actions") or ()),
        public_verification=str(trajectory.get("public_verification") or ""),
        failure_notes=notes,
    )


def build_memory_cards_v4(
    *,
    canonical_path: Path,
    snapshot_path: Path,
    verification_path: Path,
    runs: list[dict],
    path_base: Path | None = None,
    allow_legacy: bool = True,
) -> tuple[tuple[MemoryCard, ...], list[str], list[str]]:
    targets = target_ids(canonical_path)
    assert_sources_disjoint(V4_SOURCE_IDS, targets)
    chosen, ignored = select_runs(runs, V4_SOURCE_IDS, targets)
    pool = _pool_index(canonical_path)
    base = path_base or canonical_path.parents[2]
    legacy = _legacy_rows(snapshot_path)
    labels = load_source_verification(verification_path, V4_SOURCE_IDS)
    cards = []
    missing = []
    for source_id in V4_SOURCE_IDS:
        entry = pool[source_id]
        issue = _issue_text(entry, base)
        run = chosen[source_id]
        if run is not None:
            run_dir = Path(run["run_dir"])
            if "answer_isolation_pass" in run:
                isolated = run.get("answer_isolation_pass") is True
            else:
                isolated = allow_legacy
            grader = run.get("grader_status")
            passed = bool(run.get("solved")) and grader in {None, "", "pass"}
            if bool(run.get("solved")) and "answer_isolation_pass" in run and not isolated:
                raise ValueError("solved_run_without_isolation:" + source_id)
            status = "validated_fix" if passed and isolated else "failed_attempt"
            cards.append(
                _card_from_run(
                    source_id,
                    repo=entry["expected_repo"],
                    created_at=(entry.get("provenance") or {}).get("historical_pr_created_at")
                    or "1970-01-01T00:00:00+00:00",
                    version=entry["expected_base_commit"],
                    issue=issue,
                    run_dir=run_dir,
                    layout="sprint",
                    status=status,
                    origin="source_task_swebench_tests",
                    source_run=f"r{int(run['repeat'])} {run_dir}",
                )
            )
            continue
        if not allow_legacy:
            missing.append(source_id)
            continue
        row = legacy.get(source_id)
        if row is None:
            missing.append(source_id)
            continue
        source_dir = Path(row["source_dir"])
        trajectory = json.loads((source_dir / "public-trajectory.json").read_text(encoding="utf-8"))
        cards.append(
            _card_from_run(
                source_id,
                repo=row["bindings"]["repo"],
                created_at="1970-01-01T00:00:00+00:00",
                version=row["bindings"]["base_revision"],
                issue=issue or str(trajectory.get("issue_summary") or source_id),
                run_dir=source_dir,
                layout="memory_pool",
                status="unverified" if labels[source_id] == "validated_fix" else labels[source_id],
                origin="legacy_verification",
                source_run=f"legacy {source_dir}",
                legacy_trajectory=trajectory,
            )
        )
    return tuple(cards), ignored, missing


def manifest_for(
    cards: tuple[MemoryCard, ...],
    cards_bytes: bytes,
    *,
    status: str,
    coding_agent_commit: str,
    memory_source_runs_sha256: str | None,
    legacy_snapshot_sha256: str,
) -> dict:
    return {
        "schema": MANIFEST_SCHEMA,
        "cards_sha256": hashlib.sha256(cards_bytes).hexdigest(),
        "status": status,
        "coding_agent_commit": coding_agent_commit,
        "sources": [
            {
                "source_id": card.source_id,
                "status": card.verification_status,
                "label_origin": card.label_origin,
                "source_run": card.source_run.split(" ", 1)[0],
            }
            for card in cards
        ],
        "build_inputs": {
            "memory_source_runs_sha256": memory_source_runs_sha256,
            "legacy_snapshot_sha256": legacy_snapshot_sha256,
        },
    }


def cards_jsonl(cards: tuple[MemoryCard, ...]) -> bytes:
    lines = [
        json.dumps(card.model_dump(mode="json"), ensure_ascii=False, sort_keys=True) for card in cards
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
