"""Shared helpers for memory retrieval and consolidation."""

from __future__ import annotations

import re

from reposkill_agent.core.contracts import TaskSpec
from reposkill_agent.skills.domain import TASK_DOMAIN_TAGS

DOMAIN_TAGS = TASK_DOMAIN_TAGS
MECHANISM_TAGS = frozenset(
    {
        "skill_heavy",
        "memory_heavy",
        "context_heavy",
        "multi_file_api",
        "traceback_repair",
        "repo_convention",
        "repeated",
        "support",
    }
)

REPO_CONVENTIONS: dict[str, str] = {
    "medium_inventory": (
        "Return Result[T] with .ok/.value/.error from APIs; tests assert result.ok and "
        "result.value — not raw int/bool and not bare exceptions."
    ),
    "medium_config_loader": (
        "Config loader APIs return Result objects; merged config should respect layer "
        "precedence (env overrides file overrides defaults)."
    ),
    "medium_event_pipeline": (
        "Event pipeline uses Result for handler outcomes; serializer must stay backward "
        "compatible across payload versions."
    ),
    "medium_auth_rules": (
        "Authorization APIs return Result objects; role checks and token parsing should "
        "use structured errors, not bare bool or raised KeyError."
    ),
}


def domain_tags(tags: list[str]) -> set[str]:
    return {tag for tag in tags if tag in DOMAIN_TAGS}


def repo_convention_for_path(repo_path: str) -> str:
    normalized = repo_path.replace("\\", "/")
    for key, convention in REPO_CONVENTIONS.items():
        if key in normalized:
            return convention
    if "result" in normalized.lower():
        return "Prefer Result-based return values over raises or bare primitives."
    return ""


def procedural_applies(procedural_tags: list[str], task: TaskSpec) -> bool:
    task_domains = domain_tags(task.tags)
    proc_domains = domain_tags(procedural_tags)
    if task_domains and proc_domains & task_domains:
        return True
    task_tokens = set(task.tags) - MECHANISM_TAGS
    return bool(task_tokens & set(procedural_tags))


def seed_pair_task_id(holdout_task_id: str) -> str | None:
    """Map holdout task ids to their non-holdout seed task when naming allows."""
    if "_holdout_" in holdout_task_id:
        return holdout_task_id.replace("_holdout_", "_", 1)
    if holdout_task_id.endswith("_holdout_01"):
        return holdout_task_id[: -len("_holdout_01")] + "_01"
    return None


def extract_test_signals(test_output: str) -> list[str]:
    """Compact, actionable signals from pytest output."""
    if not test_output.strip():
        return []
    signals: list[str] = []
    if ".ok" in test_output or "Result" in test_output:
        signals.append("tests expect Result.ok / Result.err — not int, bool, or raise")
    if "TypeError" in test_output and "unexpected keyword argument" in test_output:
        match = re.search(r"unexpected keyword argument '(\w+)'", test_output)
        if match:
            signals.append(f"add parameter `{match.group(1)}` to match test call signature")
        else:
            signals.append("align function signature with test keyword arguments")
    if "TypeError" in test_output and "missing" in test_output and "argument" in test_output:
        signals.append("add missing parameters required by tests")
    if "AttributeError" in test_output and "has no attribute" in test_output:
        match = re.search(r"'(\w+)' object has no attribute '(\w+)'", test_output)
        if match:
            attr = match.group(2)
            got = match.group(1)
            if attr == "ok":
                signals.append(
                    f"tests expect Result.{attr} — not {got}; return Result[T] not bare {got}"
                )
            else:
                signals.append(
                    f"return type should expose `.{attr}` (got {got})"
                )
    if "AssertionError" in test_output:
        signals.append("re-read failing assertion in test output and match expected behavior")
    if "ModuleNotFoundError" in test_output or "ImportError" in test_output:
        signals.append("fix imports before changing logic")
    return signals[:4]


def python_source_files(paths: list[str], limit: int = 8) -> list[str]:
    cleaned: list[str] = []
    for path in paths:
        normalized = path.replace("\\", "/")
        if not normalized.endswith(".py"):
            continue
        if normalized.startswith("tests/") or "/tests/" in normalized:
            continue
        if "__pycache__" in normalized:
            continue
        cleaned.append(normalized)
    return cleaned[:limit]
