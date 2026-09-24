"""Developer agent for patch nodes."""

from __future__ import annotations

from reposkill_agent.adapters.base import WorkspaceAdapter
from reposkill_agent.adapters.fake_adapter import FakeAdapter
from reposkill_agent.agents.contracts import AgentContext, AgentResult, RoleAgent
from reposkill_agent.core.contracts import PatchSpec
from reposkill_agent.eval.scripted_fixes import SCRIPTED_FIXES


class DeveloperAgent(RoleAgent):
    """Handles patch node with deterministic fixes."""

    role = "developer"

    def run(self, context: AgentContext, adapter: WorkspaceAdapter) -> AgentResult:
        skill_ids = [skill.get("id", "") for skill in context.active_skills]
        strategy = self._select_strategy(context, skill_ids)

        if strategy.startswith("hard_"):
            category = strategy.removeprefix("hard_")
            patch_results = self._apply_hard_patch(category, adapter)
            serialized = [item.model_dump() for item in patch_results]
            return AgentResult(
                success=bool(serialized),
                payload={
                    "patches": serialized,
                    "skills_applied": [skill_id for skill_id in skill_ids if skill_id],
                    "patch_strategy": strategy,
                },
            )
        if strategy == "hard_blocked":
            return AgentResult(
                success=False,
                payload={
                    "patches": [],
                    "skills_applied": [skill_id for skill_id in skill_ids if skill_id],
                    "patch_strategy": strategy,
                    "error": "no skill/memory strategy available for hard task",
                },
            )

        patch_results = []
        if isinstance(adapter, FakeAdapter):
            patch_results = adapter.apply_scripted_fix(context.task.id)
        else:
            for fix in SCRIPTED_FIXES.get(context.task.id, []):
                patch_results.append(adapter.apply_patch(fix))
        serialized = [item.model_dump() for item in patch_results]
        applied = [skill_id for skill_id in skill_ids if skill_id]
        return AgentResult(
            success=bool(serialized),
            payload={
                "patches": serialized,
                "skills_applied": applied,
                "patch_strategy": strategy,
            },
        )

    def _select_strategy(self, context: AgentContext, skill_ids: list[str]) -> str:
        hard_categories = {"rename", "api", "regression", "traceback"}
        category = next((tag for tag in context.task.tags if tag in hard_categories), None)
        if category is None:
            return "scripted_fix"

        required_skill = {
            "rename": "rename_symbol_across_files",
            "api": "update_api_signature_and_callers",
            "regression": "add_regression_test_before_fix",
            "traceback": "inspect_pytest_traceback",
        }[category]
        has_skill = required_skill in skill_ids
        has_memory = self._memory_allows_category(context.memory_hints, category)
        if has_skill or has_memory:
            return f"hard_{category}"
        return "hard_blocked"

    @staticmethod
    def _memory_allows_category(memory_hints: list[dict], category: str) -> bool:
        for hint in memory_hints:
            applies = hint.get("applies_when") or []
            if category in applies:
                return True
            pattern = str(hint.get("successful_pattern", "")).lower()
            if category in pattern:
                return True
            if category in str(hint).lower():
                return True
        return False

    @staticmethod
    def _apply_hard_patch(category: str, adapter: WorkspaceAdapter) -> list:
        patches: dict[str, list[PatchSpec]] = {
            "rename": [
                PatchSpec(
                    path="app/processor.py",
                    content=(
                        '"""Text processing helpers."""\n\n\n'
                        "def clean_text(text: str) -> str:\n"
                        '    """Normalize and lowercase text."""\n'
                        '    return " ".join(text.strip().split()).lower()\n'
                    ),
                )
            ],
            "api": [
                PatchSpec(
                    path="app/math_api.py",
                    content=(
                        '"""Math API module."""\n\n\n'
                        "def scale(value: int, factor: int = 2) -> int:\n"
                        '    """Scale value by optional factor."""\n'
                        "    return value * factor\n"
                    ),
                )
            ],
            "regression": [
                PatchSpec(
                    path="app/division.py",
                    content=(
                        '"""Division utilities."""\n\n\n'
                        "def safe_divide(a: int, b: int) -> float:\n"
                        "    if b == 0:\n"
                        "        return 0\n"
                        "    return a / b\n"
                    ),
                )
            ],
            "traceback": [
                PatchSpec(
                    path="app/text_utils.py",
                    content=(
                        '"""Text utility functions."""\n\n\n'
                        "def normalize_whitespace(text: str) -> str:\n"
                        '    return " ".join(text.strip().split())\n'
                    ),
                )
            ],
        }
        return [adapter.apply_patch(patch) for patch in patches.get(category, [])]
