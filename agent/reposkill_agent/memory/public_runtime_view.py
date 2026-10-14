"""Public A5 trajectory projection bound to the immutable 11-source snapshot."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def words(text: str) -> set[str]:
    return set(re.findall(r"[a-z][a-z0-9_]{2,}", text.lower()))


@dataclass(frozen=True)
class PublicEpisode:
    source_id: str
    repo: str
    source_hash: str
    trajectory_hash: str
    snapshot_hash: str
    issue: str
    observations: tuple[str, ...]
    actions: tuple[str, ...]
    verification: str
    failure_notes: tuple[str, ...]

    def raw_text(self) -> str:
        return json.dumps({"historical_issue": self.issue[:500],
                           "public_observations": [item[:240] for item in self.observations[:8]],
                           "actions": list(self.actions[:20]), "public_verification": self.verification[:300],
                           "failure_notes": list(self.failure_notes[:4])}, ensure_ascii=False,
                          sort_keys=True, separators=(",", ":"))

    def procedure_text(self) -> str:
        changed = [action for action in self.actions if action.split(":", 1)[0] in
                   {"search_replace", "edit_file", "write_file"}]
        explored = [action for action in self.actions if action.split(":", 1)[0] in
                    {"read_file", "list_dir", "run_command"}]
        return json.dumps({"kind": "deterministic_public_procedure",
                           "historical_problem": self.issue[:500],
                           "applicability": {"repo": self.repo,
                                             "observed_paths": sorted({a.split(":", 1)[1] for a in changed if ":" in a})},
                           "exploration": explored[:12], "repair_actions": changed[:12],
                           "verification": self.verification,
                           "limitations": "Derived from public trajectory; no full private grader validation."},
                          ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def load_public_episodes(snapshot_path: Path) -> tuple[PublicEpisode, ...]:
    raw = snapshot_path.read_bytes()
    snapshot_hash = sha(raw)
    episodes = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        source = Path(row["source_dir"]).resolve(strict=True)
        trajectory_path = source / "public-trajectory.json"
        trajectory_raw = trajectory_path.read_bytes()
        if sha(trajectory_raw) != row["hashes"]["trajectory_sha256"]:
            raise ValueError("public_trajectory_hash_mismatch:" + row["source_id"])
        trajectory = json.loads(trajectory_raw)
        episodes.append(PublicEpisode(
            source_id=row["source_id"], repo=row["bindings"]["repo"],
            source_hash=row["line_sha256"], trajectory_hash=sha(trajectory_raw),
            snapshot_hash=snapshot_hash, issue=trajectory["issue_summary"],
            observations=tuple(trajectory["public_evidence"]),
            actions=tuple(trajectory["actions"]),
            verification=trajectory["public_verification"],
            failure_notes=tuple(trajectory["failure_notes"])))
    if len(episodes) != 11 or len({e.source_id for e in episodes}) != 11:
        raise ValueError("public_episode_source_count_mismatch")
    return tuple(episodes)


def select_public_episodes(episodes: tuple[PublicEpisode, ...], *, repo: str,
                           issue: str, limit: int = 2) -> tuple[PublicEpisode, ...]:
    query = words(issue)
    ranked = sorted(((len(query & words(e.issue + " " + " ".join(e.observations[:8]))), e)
                     for e in episodes if e.repo == repo),
                    key=lambda pair: (-pair[0], pair[1].source_id))
    return tuple(e for score, e in ranked if score > 0)[:limit]


def check_public_dependencies(episode: PublicEpisode, target_root: Path) -> tuple[str, str]:
    paths = {a.split(":", 1)[1] for a in episode.actions
             if a.split(":", 1)[0] in {"search_replace", "edit_file", "write_file"} and ":" in a}
    if not paths:
        return "unknown", "no_observed_repair_paths"
    existing = 0
    for name in paths:
        path = Path(name)
        if path.is_absolute() or ".." in path.parts:
            return "invalid", "unsafe_dependency_path"
        target = target_root / path
        if not target.is_file():
            return "invalid", "dependency_path_missing:" + name
        existing += 1
    return ("valid", "observed_repair_paths_present") if existing else ("unknown", "no_dependency_evidence")


class A5PublicMemoryPlugin:
    """Data-only H4 candidate policy; all execution and injection remain host-owned."""

    name = "reposkill-public"
    schema_version = "0.1"

    def __init__(self, *, variant: str, episodes: tuple[PublicEpisode, ...], repo: str,
                 issue: str, target_root: Path, max_bytes: int = 4096):
        if variant not in {"B0", "B1", "B2", "B3"}:
            raise ValueError("invalid_variant")
        self.variant, self.episodes, self.repo = variant, episodes, repo
        self.issue, self.target_root, self.max_bytes = issue, target_root, max_bytes

    async def decide(self, policy_input: dict) -> dict:
        previous = policy_input.get("state") or {}
        if previous.get("calls", 0):
            return {"schema_version": "0.1", "candidates": [],
                    "state": {"calls": previous["calls"] + 1}, "events": [], "action_proposals": []}
        candidates, decisions = [], []
        remaining = self.max_bytes
        selected = () if self.variant == "B0" else select_public_episodes(
            self.episodes, repo=self.repo, issue=self.issue)
        for episode in selected:
            validity, reason = (check_public_dependencies(episode, self.target_root)
                                if self.variant == "B3" else ("not_checked", "variant_without_gate"))
            text = episode.raw_text() if self.variant == "B1" else episode.procedure_text()
            size = len(text.encode("utf-8"))
            status = "selected" if validity in ("valid", "not_checked") and size <= remaining else (
                "rejected_" + validity if validity not in ("valid", "not_checked") else "over_budget")
            decisions.append({"source_id": episode.source_id, "status": status,
                              "reason": reason, "bytes": size})
            if status == "selected":
                remaining -= size
                candidates.append({"id": episode.source_id, "text": text,
                                   "source": episode.source_hash, "reason": "public_trajectory_derived",
                                   "valid": True, "priority": len(selected) - len(candidates),
                                   "repo_revision": policy_input.get("repo_revision")})
        if self.variant == "B0":
            overall = "not_selected"
        elif not selected:
            overall = "no_relevant_memory"
        elif candidates:
            overall = "selected"
        elif any(d["status"] == "rejected_invalid" for d in decisions):
            overall = "rejected_invalid"
        elif any(d["status"] == "rejected_unknown" for d in decisions):
            overall = "rejected_unknown"
        else:
            overall = "not_selected"
        return {"schema_version": "0.1", "candidates": candidates,
                "state": {"calls": 1}, "action_proposals": [],
                "events": [{"type": "a5.public_memory_decision", "variant": self.variant,
                            "status": overall, "items": decisions}]}
