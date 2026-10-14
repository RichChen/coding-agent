"""Context expansion helpers for needs_more_context recovery."""

from __future__ import annotations

from pathlib import PurePosixPath

from reposkill_agent.adapters.base import WorkspaceAdapter
from reposkill_agent.core.contracts import TaskSpec

MAX_PATHS_PER_ROUND = 3
MAX_TOTAL_ALLOWED_PATHS = 6


def is_test_path(path: str) -> bool:
    """True when path lives under a tests/ directory (read-only for LLM patches)."""
    normalized = path.replace("\\", "/")
    return normalized.startswith("tests/") or "/tests/" in normalized


def is_writable_patch_path(path: str) -> bool:
    """Paths the developer agent may apply full-file writes to."""
    return not is_test_path(path)


def collect_requested_context(previous_actions: list[dict]) -> list[str]:
    """Read requested_context from the most recent failed patch action."""
    for action in reversed(previous_actions):
        if action.get("node_id") != "patch":
            continue
        requested = action.get("requested_context")
        if isinstance(requested, list) and requested:
            return [str(item) for item in requested]
        if action.get("llm_error_type") == "needs_more_context":
            return ["tests", "callers", "package_modules"]
    return []


def expand_allowed_paths(
    *,
    adapter: WorkspaceAdapter,
    task: TaskSpec,
    requested_context: list[str],
    current_paths: set[str],
) -> tuple[list[str], list[str]]:
    """Add up to MAX_PATHS_PER_ROUND paths; respect MAX_TOTAL_ALLOWED_PATHS total."""
    if not requested_context:
        return [], []

    repo_files = adapter.list_files("**/*.py")
    keywords = " ".join(requested_context).lower()
    candidates: list[str] = []

    if any(token in keywords for token in ("test", "traceback", "pytest", "caller")):
        candidates.extend(
            path
            for path in repo_files
            if path.startswith("tests/") or "/tests/" in path.replace("\\", "/")
        )

    for expected in task.expected_files:
        parent = PurePosixPath(expected.replace("\\", "/")).parent.as_posix()
        if parent and parent != ".":
            prefix = f"{parent}/"
            candidates.extend(
                path
                for path in repo_files
                if path.replace("\\", "/").startswith(prefix)
            )

    if any(token in keywords for token in ("config", "schema", "convention", "package")):
        candidates.extend(
            path
            for path in repo_files
            if any(part in path.lower() for part in ("config", "schema"))
        )

    if "caller" in keywords or "symbol" in keywords:
        for path in repo_files:
            if path in current_paths:
                continue
            try:
                text = adapter.read_file(path)
            except OSError:
                continue
            for expected in task.expected_files:
                stem = PurePosixPath(expected.replace("\\", "/")).stem
                if stem and stem in text:
                    candidates.append(path)

    added: list[str] = []
    reasons: list[str] = []
    seen = set(current_paths)
    for path in candidates:
        normalized = path.replace("\\", "/")
        if normalized in seen:
            continue
        if len(added) >= MAX_PATHS_PER_ROUND:
            break
        if len(seen) >= MAX_TOTAL_ALLOWED_PATHS:
            break
        if normalized not in repo_files and path not in repo_files:
            continue
        added.append(normalized)
        seen.add(normalized)
        reasons.append(f"context:{keywords[:48]}")

    return added, reasons


def merge_expanded_paths(existing: list[str], new_paths: list[str]) -> list[str]:
    """Merge path lists without duplicates, capped at MAX_TOTAL_ALLOWED_PATHS."""
    merged: list[str] = []
    seen: set[str] = set()
    for path in [*existing, *new_paths]:
        normalized = path.replace("\\", "/")
        if normalized in seen:
            continue
        if len(merged) >= MAX_TOTAL_ALLOWED_PATHS:
            break
        merged.append(normalized)
        seen.add(normalized)
    return merged
