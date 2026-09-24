"""Task category labels for ablation reporting (Phase 6 + Phase 7)."""

from __future__ import annotations

PHASE7_CATEGORY_ORDER = [
    "skill_heavy",
    "memory_heavy",
    "context_heavy",
    "multi_file_api",
    "traceback_repair",
    "repo_convention",
]

LEGACY_CATEGORY_ORDER = [
    "import",
    "logic",
    "feature",
    "rename",
    "api",
    "regression",
    "traceback",
    "repeated",
]


def task_category(tags: list[str]) -> str:
    """Return the primary mechanism/category label for a task tag set."""
    for key in PHASE7_CATEGORY_ORDER + LEGACY_CATEGORY_ORDER:
        if key in tags:
            return key
    return "other"
