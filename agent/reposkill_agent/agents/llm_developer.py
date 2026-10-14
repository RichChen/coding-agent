"""LLM-backed developer agent for patch nodes."""

from __future__ import annotations

import os
from typing import Any

from reposkill_agent.adapters.base import WorkspaceAdapter
from reposkill_agent.agents.contracts import AgentContext, AgentResult, RoleAgent
from reposkill_agent.core.context_expansion import (
    MAX_TOTAL_ALLOWED_PATHS,
    is_writable_patch_path,
)
from reposkill_agent.core.contracts import PatchSpec
from reposkill_agent.llm.client import ModelClientProtocol
from reposkill_agent.llm.prompts import (
    build_json_repair_prompt,
    build_system_prompt,
    build_user_prompt,
    prompt_length_summary,
)
from reposkill_agent.llm.schemas import PatchPlan

MAX_FILES_PER_PATCH = 3


class LLMDeveloperAgent(RoleAgent):
    """Generate full-file edits via an OpenAI-compatible LLM."""

    role = "developer"

    def __init__(
        self,
        model_client: ModelClientProtocol,
        *,
        max_calls_per_task: int = 3,
        call_state: dict[str, Any] | None = None,
        max_completion_tokens: int | None = None,
    ) -> None:
        self.model_client = model_client
        self.max_calls_per_task = max_calls_per_task
        self.call_state = call_state if call_state is not None else {}
        self.max_completion_tokens = max_completion_tokens or int(
            os.environ.get("LLM_MAX_TOKENS", "4096")
        )

    def run(self, context: AgentContext, adapter: WorkspaceAdapter) -> AgentResult:
        metrics = self._empty_metrics()
        if int(self.call_state.get("llm_call_count", 0)) >= self.max_calls_per_task:
            metrics["llm_error_type"] = "llm_call_budget_exceeded"
            return AgentResult(
                success=False,
                payload={
                    "patches": [],
                    "patch_strategy": "llm",
                    "error": "llm call budget exceeded",
                    "llm_metrics": metrics,
                },
            )

        context_paths = self._context_paths(context)
        writable_paths = self._writable_paths(context_paths)
        file_contents = self._read_files(adapter, context_paths)
        test_output = self._latest_test_output(context)
        repo_files = adapter.list_files("**/*.py")[:60]

        system = build_system_prompt()
        user = build_user_prompt(
            context=context,
            file_contents=file_contents,
            allowed_paths=sorted(writable_paths),
            repo_files=repo_files,
            test_output=test_output,
        )

        raw, call_metrics = self._call_llm(system=system, user=user)
        metrics = self._merge_call_metrics(metrics, call_metrics)

        metrics["prompt_summary"] = {
            **prompt_length_summary(system, user),
            "allowed_paths": sorted(writable_paths),
            "readable_paths": sorted(context_paths),
            "skill_injected_count": len(context.active_skills),
            "memory_injected_count": len(context.memory_hints),
        }

        if raw.get("error_type") == "llm_parse_error":
            metrics["llm_parse_error_count"] = int(metrics.get("llm_parse_error_count", 0)) + 1
            repaired_raw, repair_metrics = self._attempt_json_repair(
                raw=raw,
                allowed_paths=sorted(writable_paths),
            )
            metrics = self._merge_call_metrics(metrics, repair_metrics)
            if repaired_raw is not None:
                raw = repaired_raw
            else:
                metrics["llm_error_type"] = "llm_parse_error"
                return AgentResult(
                    success=False,
                    payload={
                        "patches": [],
                        "patch_strategy": "llm",
                        "error": raw.get("message", "llm_parse_error"),
                        "llm_metrics": metrics,
                    },
                )

        if raw.get("error_type"):
            metrics["llm_error_type"] = str(raw["error_type"])
            return AgentResult(
                success=False,
                payload={
                    "patches": [],
                    "patch_strategy": "llm",
                    "error": raw.get("message", raw["error_type"]),
                    "llm_metrics": metrics,
                },
            )

        try:
            plan = PatchPlan.model_validate(raw)
        except Exception as exc:
            metrics["llm_parse_error_count"] = int(metrics.get("llm_parse_error_count", 0)) + 1
            metrics["llm_error_type"] = "llm_parse_error"
            return AgentResult(
                success=False,
                payload={
                    "patches": [],
                    "patch_strategy": "llm",
                    "error": f"patch plan validation failed: {exc}",
                    "llm_metrics": metrics,
                },
            )

        if plan.needs_more_context or not plan.edits:
            metrics["llm_error_type"] = "needs_more_context"
            return AgentResult(
                success=False,
                payload={
                    "patches": [],
                    "patch_strategy": "llm",
                    "error": "llm requested more context or returned no edits",
                    "llm_metrics": metrics,
                    "patch_plan_summary": plan.summary[:200],
                    "requested_context": list(plan.requested_context),
                },
            )

        edits = plan.edits[:MAX_FILES_PER_PATCH]
        patch_results = []
        rejected = 0
        for edit in edits:
            normalized_path = edit.path.replace("\\", "/")
            if normalized_path not in writable_paths or not is_writable_patch_path(
                normalized_path
            ):
                rejected += 1
                continue
            patch_results.append(
                adapter.apply_patch(
                    PatchSpec(path=edit.path, content=edit.content, mode="write")
                )
            )

        if rejected:
            metrics["llm_patch_rejected_count"] = rejected
            if not patch_results:
                metrics["llm_error_type"] = "patch_rejected_path_scope"
                return AgentResult(
                    success=False,
                    payload={
                        "patches": [],
                        "patch_strategy": "llm",
                        "error": "all proposed edits were outside allowed path scope",
                        "llm_metrics": metrics,
                    },
                )

        metrics["llm_patch_applied_count"] = len(patch_results)
        serialized = [item.model_dump() for item in patch_results]
        return AgentResult(
            success=bool(serialized),
            payload={
                "patches": serialized,
                "patch_strategy": "llm",
                "patch_plan_summary": plan.summary[:200],
                "llm_metrics": metrics,
            },
        )

    def _call_llm(self, *, system: str, user: str) -> tuple[dict[str, Any], dict[str, Any]]:
        if int(self.call_state.get("llm_call_count", 0)) >= self.max_calls_per_task:
            return (
                {"error_type": "llm_call_budget_exceeded", "message": "llm call budget exceeded"},
                {"llm_call_count": 0},
            )
        self.call_state["llm_call_count"] = int(self.call_state.get("llm_call_count", 0)) + 1
        raw = self.model_client.complete_json(
            system=system,
            user=user,
            temperature=0.0,
            max_tokens=self.max_completion_tokens,
        )
        call_metrics = {
            "llm_call_count": 1,
            "llm_wall_time_ms": float(raw.get("llm_wall_time_ms", 0.0)),
            "llm_prompt_tokens_estimate": int(raw.get("llm_prompt_tokens_estimate", 0)),
            "llm_completion_tokens_estimate": int(
                raw.get("llm_completion_tokens_estimate", 0)
            ),
            "token_estimate_mode": raw.get("token_estimate_mode", "char_approx"),
        }
        return raw, call_metrics

    def _attempt_json_repair(
        self,
        *,
        raw: dict[str, Any],
        allowed_paths: list[str],
    ) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        if int(self.call_state.get("llm_call_count", 0)) >= self.max_calls_per_task:
            return None, {
                "llm_parse_repair_attempt_total": 0,
                "llm_parse_repair_success_total": 0,
            }
        preview = str(raw.get("raw_content_preview", raw.get("message", "")))
        repair_user = build_json_repair_prompt(
            allowed_paths=allowed_paths,
            raw_preview=preview,
        )
        self.call_state["llm_call_count"] = int(self.call_state.get("llm_call_count", 0)) + 1
        repaired = self.model_client.complete_json(
            system="Return valid JSON only.",
            user=repair_user,
            temperature=0.0,
            max_tokens=self.max_completion_tokens,
        )
        repair_metrics = {
            "llm_call_count": 1,
            "llm_parse_repair_attempt_total": 1,
            "llm_parse_repair_success_total": 0,
            "llm_wall_time_ms": float(repaired.get("llm_wall_time_ms", 0.0)),
            "llm_prompt_tokens_estimate": int(repaired.get("llm_prompt_tokens_estimate", 0)),
            "llm_completion_tokens_estimate": int(
                repaired.get("llm_completion_tokens_estimate", 0)
            ),
        }
        if repaired.get("error_type"):
            return None, repair_metrics
        try:
            PatchPlan.model_validate(repaired)
        except Exception:
            return None, repair_metrics
        repair_metrics["llm_parse_repair_success_total"] = 1
        return repaired, repair_metrics

    @staticmethod
    def _merge_call_metrics(base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
        merged = dict(base)
        for key, value in extra.items():
            if key.endswith("_total") or key in {
                "llm_call_count",
                "llm_parse_error_count",
                "llm_patch_rejected_count",
                "llm_patch_applied_count",
            }:
                merged[key] = int(merged.get(key, 0)) + int(value)
            elif key == "llm_wall_time_ms":
                merged[key] = float(merged.get(key, 0.0)) + float(value)
            elif key in {"llm_prompt_tokens_estimate", "llm_completion_tokens_estimate"}:
                merged[key] = int(merged.get(key, 0)) + int(value)
            else:
                merged[key] = value
        return merged

    @staticmethod
    def _empty_metrics() -> dict[str, Any]:
        return {
            "llm_call_count": 0,
            "llm_parse_error_count": 0,
            "llm_patch_rejected_count": 0,
            "llm_patch_applied_count": 0,
            "llm_prompt_tokens_estimate": 0,
            "llm_completion_tokens_estimate": 0,
            "llm_wall_time_ms": 0.0,
            "llm_error_type": "",
            "token_estimate_mode": "char_approx",
            "llm_parse_repair_attempt_total": 0,
            "llm_parse_repair_success_total": 0,
        }

    @staticmethod
    def _context_paths(context: AgentContext) -> set[str]:
        """Readable paths for prompt context (includes tests/ from expansion)."""
        allowed: list[str] = []
        seen: set[str] = set()
        for path in [
            *context.task.expected_files,
            *context.expanded_paths,
        ]:
            normalized = path.replace("\\", "/")
            if normalized in seen:
                continue
            allowed.append(normalized)
            seen.add(normalized)
        for action in context.previous_actions:
            matches = action.get("matches")
            if isinstance(matches, list):
                for path in matches:
                    normalized = str(path).replace("\\", "/")
                    if normalized in seen:
                        continue
                    allowed.append(normalized)
                    seen.add(normalized)
        return set(allowed[:MAX_TOTAL_ALLOWED_PATHS])

    @staticmethod
    def _writable_paths(context_paths: set[str]) -> set[str]:
        """Patch targets: context paths minus read-only tests/."""
        return {path for path in context_paths if is_writable_patch_path(path)}

    @staticmethod
    def _read_files(adapter: WorkspaceAdapter, paths: set[str]) -> dict[str, str]:
        contents: dict[str, str] = {}
        for path in sorted(paths):
            try:
                contents[path] = adapter.read_file(path)
            except OSError:
                contents[path] = ""
        return contents

    @staticmethod
    def _latest_test_output(context: AgentContext) -> str:
        chunks: list[str] = []
        for action in reversed(context.previous_actions):
            test_result = action.get("test_result")
            if isinstance(test_result, dict):
                stdout = str(test_result.get("stdout", ""))
                stderr = str(test_result.get("stderr", ""))
                chunks.append(stdout)
                chunks.append(stderr)
                break
        return "\n".join(part for part in chunks if part).strip()
