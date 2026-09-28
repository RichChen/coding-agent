"""Build memory cards from a handoff. Source ids come from the file, not a fixed list."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from reposkill_agent.memory.cards_v4 import (
    PilotTargetInSources,
    _card_from_run,
    _issue_text,
    _pool_index,
    select_runs,
    target_ids,
)
from reposkill_agent.memory.records import MemoryCard

V2_SCHEMA = "sprint5.memory-source-runs.v2"
V1_SCHEMA = "sprint4.memory-source-runs.v1"
MANIFEST_SCHEMA = "memory-cards.v5.manifest"


class HandoffFieldMissing(ValueError):
    """A run is missing repo or created_at. Do not fill a default."""


def published_sha256(path: Path) -> str:
    """UTF-8 bytes with LF newlines. Matches the harness handoff convention."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")).hexdigest()


def load_handoff_document(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") not in {V1_SCHEMA, V2_SCHEMA}:
        raise ValueError("unexpected_memory_source_runs_schema")
    runs = data.get("runs")
    if not isinstance(runs, list) or not runs:
        raise ValueError("memory_source_runs_not_a_list")
    return data


def runs_with_identity(data: dict, pool: dict[str, dict]) -> list[dict]:
    """v2 runs must already carry repo and created_at. v1 is interim and looks them up."""
    enriched = []
    interim = data.get("schema") != V2_SCHEMA
    for run in data["runs"]:
        source_id = str(run.get("source_id") or "")
        repo = run.get("repo")
        created_at = run.get("created_at")
        if interim and (not repo or not created_at):
            entry = pool.get(source_id)
            provenance = (entry or {}).get("provenance") or {}
            repo = repo or (entry or {}).get("expected_repo")
            created_at = created_at or provenance.get("historical_pr_created_at")
        if not isinstance(repo, str) or not repo:
            raise HandoffFieldMissing("repo_missing:" + source_id)
        if not isinstance(created_at, str) or not created_at:
            raise HandoffFieldMissing("created_at_missing:" + source_id)
        enriched.append({**run, "repo": repo, "created_at": created_at})
    return enriched


def assert_isolated(runs: list[dict], targets: set[str]) -> None:
    leaked = sorted({run["source_id"] for run in runs if run["source_id"] in targets})
    if leaked:
        raise PilotTargetInSources(leaked)
    bad = [run["source_id"] for run in runs if run.get("answer_isolation_pass") is not True]
    if bad:
        raise ValueError("isolation_failed")


def build_cards_from_handoff(
    handoff_path: Path,
    *,
    canonical_path: Path,
    path_base: Path,
) -> tuple[tuple[MemoryCard, ...], str]:
    data = load_handoff_document(handoff_path)
    targets = target_ids(canonical_path)
    pool = _pool_index(canonical_path)
    runs = runs_with_identity(data, pool)
    assert_isolated(runs, targets)
    source_ids = tuple(dict.fromkeys(run["source_id"] for run in runs))
    chosen, _ignored = select_runs(runs, source_ids, targets)
    cards = []
    for source_id in source_ids:
        run = chosen[source_id]
        if run is None:
            raise ValueError("run_not_selected:" + source_id)
        entry = pool.get(source_id) or {}
        version = str(run.get("base_commit") or entry.get("expected_base_commit") or "")
        issue = str(run.get("issue_text") or "") or _issue_text(entry, path_base)
        if len(version) < 7 or not issue:
            raise HandoffFieldMissing("issue_or_version_missing:" + source_id)
        isolated = run.get("answer_isolation_pass") is True
        passed = bool(run.get("solved")) and run.get("grader_status") in {None, "", "pass"} and isolated
        status = "validated_fix" if passed else "failed_attempt"
        cards.append(
            _card_from_run(
                source_id,
                repo=run["repo"],
                created_at=run["created_at"],
                version=version,
                issue=issue,
                run_dir=Path(run["run_dir"]),
                layout=str(run.get("layout") or "sprint"),
                status=status,
                origin="source_task_swebench_tests",
                source_run=f"r{int(run['repeat'])} {run['run_dir']}",
            )
        )
    status_name = "final" if data.get("schema") == V2_SCHEMA else "interim"
    return tuple(cards), status_name


def cards_jsonl(cards: tuple[MemoryCard, ...]) -> bytes:
    lines = [
        json.dumps(card.model_dump(mode="json"), ensure_ascii=False, sort_keys=True) for card in cards
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")


def manifest_for(cards: tuple[MemoryCard, ...], payload: bytes, *, status: str, commit: str, handoff_sha: str | None, handoff_schema: str) -> dict:
    return {
        "schema": MANIFEST_SCHEMA,
        "cards_sha256": hashlib.sha256(payload).hexdigest(),
        "status": status,
        "coding_agent_commit": commit,
        "sources": [
            {
                "source_id": card.source_id,
                "repo": card.repo,
                "created_at": card.created_at,
                "status": card.verification_status,
                "label_origin": card.label_origin,
                "source_run": card.source_run.split(" ", 1)[0],
            }
            for card in cards
        ],
        "build_inputs": {
            "memory_source_runs_sha256": handoff_sha if status == "final" else None,
            "handoff_schema": handoff_schema,
            "interim_handoff_sha256": None if status == "final" else handoff_sha,
        },
    }
