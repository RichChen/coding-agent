"""Task graph runner for Phase 2 planner experiments."""

from __future__ import annotations

import shutil
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from reposkill_agent.adapters.base import WorkspaceAdapter
from reposkill_agent.adapters.openhands_adapter import OpenHandsAdapter
from reposkill_agent.agents import (
    AgentContext,
    DeveloperAgent,
    LLMDeveloperAgent,
    LocatorAgent,
    ManagerAgent,
    MemoryCuratorAgent,
    QAAgent,
    RoleAgent,
)
from reposkill_agent.core.context_expansion import merge_expanded_paths
from reposkill_agent.core.contracts import GraphMetrics, GraphRunResult, TaskSpec, TestResult
from reposkill_agent.core.planner import TaskGraphPlanner
from reposkill_agent.core.task_graph import TaskNode
from reposkill_agent.core.trace import TraceWriter
from reposkill_agent.eval.injection_policy import (
    apply_memory_policy,
    apply_skill_policy,
    resolve_augmentation_policy,
)
from reposkill_agent.eval.scripted_fixes import SCRIPTED_FIXES
from reposkill_agent.llm.client import ModelClientProtocol
from reposkill_agent.memory import (
    EpisodicStore,
    MemoryConsolidator,
    MemoryRetriever,
    ProceduralStore,
    RepoProfileStore,
)
from reposkill_agent.memory.lightweight_snapshot import (
    LightweightMemorySnapshot,
    prepare_lightweight_injection,
)
from reposkill_agent.skills import SkillRegistry, SkillRetriever, SkillValidator
from reposkill_agent.skills.models import SkillEvidenceContext

AdapterKind = Literal["fake", "openhands"]
ExecutionMode = Literal["single_graph", "role_agents"]
DeveloperMode = Literal["deterministic", "llm"]


class TaskGraphRunner:
    """Execute planner-generated task graphs with observe/replan loop."""

    def __init__(
        self,
        adapter: AdapterKind = "fake",
        trace_dir: Path | None = None,
        work_dir: Path | None = None,
        max_replans: int = 1,
        use_skills: bool = False,
        skill_library_dir: Path | None = None,
        use_memory: bool = False,
        memory_dir: Path | None = None,
        execution_mode: ExecutionMode = "role_agents",
        allow_prefix_scripted_fixes: bool = True,
        developer_mode: DeveloperMode = "deterministic",
        model_client: ModelClientProtocol | None = None,
        max_llm_calls_per_task: int = 3,
        lightweight_memory_snapshot: LightweightMemorySnapshot | None = None,
        lightweight_memory_variant: Literal["B0", "B1", "B2", "B3"] | None = None,
        lightweight_memory_repo: str | None = None,
        lightweight_memory_base_revision: str | None = None,
        lightweight_memory_source_tree_hash: str | None = None,
    ) -> None:
        self.adapter_kind = adapter
        self.trace_dir = trace_dir or Path("traces")
        self.work_dir = work_dir or self.trace_dir / "graph_workspaces"
        self.planner = TaskGraphPlanner(max_replans=max_replans)
        self.use_skills = use_skills
        self.skill_registry = SkillRegistry(
            skill_library_dir or Path("reposkill_agent/skills/library")
        )
        self.skill_retriever = SkillRetriever()
        self.skill_validator = SkillValidator()
        self.use_memory = use_memory
        self.memory_dir = memory_dir or Path("traces/memory")
        self.execution_mode = execution_mode
        self.allow_prefix_scripted_fixes = allow_prefix_scripted_fixes
        self.developer_mode = developer_mode
        self.model_client = model_client
        self.max_llm_calls_per_task = max_llm_calls_per_task
        if (lightweight_memory_snapshot is None) != (lightweight_memory_variant is None):
            raise ValueError("lightweight_snapshot_and_variant_must_be_configured_together")
        self.lightweight_memory_snapshot = lightweight_memory_snapshot
        self.lightweight_memory_variant = lightweight_memory_variant
        self.lightweight_memory_repo = lightweight_memory_repo
        self.lightweight_memory_base_revision = lightweight_memory_base_revision
        self.lightweight_memory_source_tree_hash = lightweight_memory_source_tree_hash
        self.llm_call_state: dict[str, object] = {"llm_call_count": 0}
        self._augmentation_policy = None
        self.episodic_store = EpisodicStore(self.memory_dir)
        self.procedural_store = ProceduralStore(self.memory_dir)
        self.repo_profile_store = RepoProfileStore(self.memory_dir)
        self.memory_retriever = MemoryRetriever(
            episodic_store=self.episodic_store,
            procedural_store=self.procedural_store,
            repo_profile_store=self.repo_profile_store,
        )
        self.memory_consolidator = MemoryConsolidator()
        self.memory_curator = MemoryCuratorAgent()
        self.role_agents = self._build_role_agents()

    def run(self, task: TaskSpec) -> GraphRunResult:
        run_id = uuid.uuid4().hex[:12]
        trace_path = self.trace_dir / f"{task.id}_graph_{run_id}.jsonl"
        trace = TraceWriter(trace_path, run_id=run_id, task_id=task.id)
        workspace = self._prepare_workspace(task, run_id)
        adapter = self._bind_adapter(workspace)

        started = time.perf_counter()
        trace.emit(
            "run_start",
            {"task_id": task.id, "adapter": adapter.name, "protocol_mode": "diagnostic_oracle"},
        )

        inspection = adapter.inspect_repo(task)
        trace.emit("inspect", inspection.model_dump(), agent_role="manager")

        actions: list[dict] = []
        roles_executed: list[str] = []
        steps = 0
        replan_count = 0
        failed_node_id: str | None = None
        final_test_result: TestResult | None = None
        final_diff = ""
        skill_stats = {
            "protocol_mode": "diagnostic_oracle",
            "skill_retrieved_count": 0,
            "skill_validated_count": 0,
            "skill_candidate_count": 0,
            "skill_injected_count": 0,
            "skill_gated_count": 0,
            "skill_negative_transfer_count": 0,
            "skill_ids_used": [],
            "skill_used_in_run": 0,
            "skill_execution_mode": "skill_aware_trace",
            "memory_retrieval_count": 0,
            "memory_candidate_count": 0,
            "memory_injected_count": 0,
            "memory_source_task_ids": [],
            "memory_useful_count": 0,
            "memory_stale_or_wrong_count": 0,
            "role_handoff_count": 0,
            "agent_roles_used": [],
            "llm_call_count": 0,
            "llm_parse_error_count": 0,
            "llm_patch_rejected_count": 0,
            "llm_patch_applied_count": 0,
            "llm_prompt_tokens_estimate": 0,
            "llm_completion_tokens_estimate": 0,
            "llm_wall_time_ms": 0.0,
            "llm_error_type": "",
            "developer_mode": self.developer_mode,
            "context_expansion_count": 0,
            "allowed_path_added_count": 0,
            "needs_more_context_recovered_count": 0,
            "llm_parse_repair_attempt_total": 0,
            "llm_parse_repair_success_total": 0,
            "augmentation_policy": "",
            "skill_suppressed_by_policy": 0,
            "memory_suppressed_by_policy": 0,
        }
        self.llm_call_state["llm_call_count"] = 0
        expanded_paths: list[str] = []
        awaiting_context_recovery = False
        repo_fingerprint = self.memory_consolidator.repo_fingerprint(task)
        full_stack = self.use_skills and self.use_memory
        base_policy = resolve_augmentation_policy(task, full_stack=full_stack)
        self._augmentation_policy = base_policy
        if base_policy is not None:
            skill_stats["augmentation_policy"] = base_policy.name

        while True:
            plan = self.planner.create_plan(task)
            trace.emit(
                "plan_created",
                {
                    "planner_version": plan.graph.planner_version,
                    "node_ids": [node.id for node in plan.graph.nodes],
                    "rationale": plan.rationale,
                    "replan_count": replan_count,
                },
                agent_role="manager",
            )

            for node in plan.graph.nodes:
                node_role = self._node_role(node.owner)
                self._emit_node(trace, node, "node_start", "running", agent_role=node_role)
                steps += 1
                effective_memory_hints: list[dict] = []
                effective_patch_policy = self._augmentation_policy if full_stack else None
                context_recovery_patch = (
                    node.id == "patch" and awaiting_context_recovery and full_stack
                )
                if context_recovery_patch:
                    effective_patch_policy = resolve_augmentation_policy(
                        task,
                        full_stack=True,
                        context_recovery_patch=True,
                    )
                    if effective_patch_policy is not None:
                        skill_stats["augmentation_policy"] = effective_patch_policy.name
                if node.id == "patch" and self.use_memory:
                    effective_memory_hints = self._resolve_memory_hints(
                        task,
                        repo_fingerprint,
                        actions,
                        effective_patch_policy,
                        skill_stats,
                    )
                success, payload = self._execute_node(
                    node,
                    adapter,
                    task,
                    replan_count,
                    actions,
                    skill_stats,
                    effective_memory_hints,
                    expanded_paths,
                    patch_policy=effective_patch_policy,
                )
                trace_payload = {k: v for k, v in payload.items() if k != "test_result_obj"}
                actions.append({"node_id": node.id, "success": success, **trace_payload})
                roles_executed.append(node_role)
                if node.id == "locate":
                    new_paths = payload.get("expanded_paths") or []
                    if new_paths:
                        expanded_paths = merge_expanded_paths(expanded_paths, new_paths)
                        skill_stats["context_expansion_count"] = (
                            int(skill_stats["context_expansion_count"]) + 1
                        )
                        skill_stats["allowed_path_added_count"] = int(
                            skill_stats["allowed_path_added_count"]
                        ) + len(new_paths)
                if node.id == "test":
                    final_test_result = payload["test_result_obj"]
                if node.id == "patch":
                    final_diff = adapter.produce_diff()
                    trace.emit(
                        "diff",
                        {"diff": final_diff, "length": len(final_diff)},
                        agent_role="developer",
                    )
                    llm_metrics = payload.get("llm_metrics") or {}
                    llm_error = str(llm_metrics.get("llm_error_type", ""))
                    if llm_error == "needs_more_context":
                        awaiting_context_recovery = True
                    elif success and awaiting_context_recovery:
                        skill_stats["needs_more_context_recovered_count"] = (
                            int(skill_stats["needs_more_context_recovered_count"]) + 1
                        )
                        awaiting_context_recovery = False
                if success:
                    self._emit_node(
                        trace,
                        node,
                        "node_end",
                        "passed",
                        trace_payload,
                        agent_role=node_role,
                    )
                    continue
                failed_node_id = node.id
                self._emit_node(
                    trace,
                    node,
                    "node_end",
                    "failed",
                    trace_payload,
                    agent_role=node_role,
                )
                break
            else:
                failed_node_id = None

            test_passed = bool(final_test_result and final_test_result.passed)
            decision = self.planner.observe_and_decide_replan(
                current_replans=replan_count,
                failed_node_id=failed_node_id,
                test_passed=test_passed,
            )
            trace.emit("replan", decision.model_dump(), agent_role="manager")
            if not decision.should_replan:
                break
            replan_count += 1

        wall_time_ms = (time.perf_counter() - started) * 1000
        if final_test_result is None:
            final_test_result = adapter.run_tests(task.test_command)
        if self.use_skills:
            used = int(skill_stats.get("skill_injected_count", 0)) > 0
            failed_after_skill = used and (not final_test_result.passed)
            skill_stats["skill_negative_transfer_count"] = 1 if failed_after_skill else 0
        if self.use_memory:
            injected = int(skill_stats.get("memory_injected_count", 0))
            if final_test_result.passed and injected > 0:
                skill_stats["memory_useful_count"] = 1
            elif injected > 0 and not final_test_result.passed:
                skill_stats["memory_stale_or_wrong_count"] = 1
        unique_roles = list(dict.fromkeys(roles_executed))
        handoff_count = 0
        for left, right in zip(roles_executed, roles_executed[1:]):
            if left != right:
                handoff_count += 1
        skill_stats["agent_roles_used"] = unique_roles
        skill_stats["role_handoff_count"] = handoff_count
        metrics = GraphMetrics(
            task_id=task.id,
            success=final_test_result.passed,
            steps=steps,
            wall_time_ms=wall_time_ms,
            replan_count=replan_count,
            test_passed=final_test_result.passed,
            adapter=adapter.name,
            trace_path=str(trace_path),
            finished_at=datetime.now(UTC),
            extra=skill_stats,
        )
        trace.emit("metric", metrics.model_dump(mode="json"), agent_role="manager")
        trace.emit("run_end", {"success": metrics.success}, agent_role="manager")
        run_result = GraphRunResult(
            task=task,
            metrics=metrics,
            diff=final_diff,
            inspection=inspection,
            test_result=final_test_result,
            actions=actions,
        )
        self._persist_memory(run_result)
        self._augmentation_policy = None
        return run_result

    def _execute_node(
        self,
        node: TaskNode,
        adapter: WorkspaceAdapter,
        task: TaskSpec,
        replan_count: int,
        previous_actions: list[dict],
        skill_stats: dict[str, object],
        memory_hints: list[dict],
        expanded_paths: list[str],
        patch_policy=None,
    ) -> tuple[bool, dict]:
        role_agent = self.role_agents.get(node.owner)
        if self.execution_mode == "single_graph":
            return self._single_graph_execute(
                node=node,
                adapter=adapter,
                task=task,
                replan_count=replan_count,
                previous_actions=previous_actions,
                memory_hints=memory_hints,
                skill_stats=skill_stats,
                expanded_paths=expanded_paths,
                patch_policy=patch_policy,
            )
        if role_agent is None:
            return False, {"error": f"unknown node owner: {node.owner}"}
        active_skills: list[dict] = []
        if self.use_skills and node.id == "patch":
            selection = self._select_skills(
                task,
                previous_actions,
                adapter,
                skill_stats,
                patch_policy=patch_policy,
            )
            active_skills = [skill.model_dump() for skill in selection.selected]
        context = AgentContext(
            task=task,
            node=node,
            replan_count=replan_count,
            previous_actions=previous_actions,
            active_skills=active_skills,
            memory_hints=memory_hints,
            expanded_paths=expanded_paths,
        )
        result = role_agent.run(context, adapter)
        self._merge_llm_metrics(skill_stats, result.payload.get("llm_metrics"))
        return result.success, result.payload

    def _persist_memory(self, run_result: GraphRunResult) -> None:
        if not self.use_memory:
            return
        episodic = self.memory_consolidator.build_episodic(run_result)
        self.episodic_store.append(episodic)
        profile = self.memory_consolidator.build_repo_profile(
            run_result.task,
            run_result.inspection,
        )
        self.repo_profile_store.upsert(profile)
        procedural = self.memory_curator.curate(run_result)
        if procedural is not None:
            self.procedural_store.append(procedural)

    def _prepare_workspace(self, task: TaskSpec, run_id: str) -> Path:
        dest = self.work_dir / f"{task.id}_{run_id}"
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(task.repo_path, dest)
        return dest

    def _resolve_memory_hints(
        self,
        task: TaskSpec,
        repo_fingerprint: str,
        previous_actions: list[dict],
        policy,
        skill_stats: dict[str, object],
    ) -> list[dict]:
        if self.lightweight_memory_snapshot is not None:
            plan = prepare_lightweight_injection(
                self.lightweight_memory_snapshot,
                self.lightweight_memory_variant or "B0",
                decision_id=f"a5:{task.id}:{uuid.uuid4().hex[:12]}",
                repo=self.lightweight_memory_repo,
                base_revision=self.lightweight_memory_base_revision,
                source_tree_hash=self.lightweight_memory_source_tree_hash,
                max_records=2,
                max_bytes=4096,
            )
            hints = list(plan.hints)
            skill_stats["memory_candidate_count"] = (
                int(skill_stats.get("memory_candidate_count", 0))
                + self.lightweight_memory_snapshot.internal_usable_count
            )
            skill_stats["memory_injected_count"] = int(
                skill_stats.get("memory_injected_count", 0)
            ) + len(hints)
            skill_stats["memory_retrieval_count"] = int(
                skill_stats.get("memory_retrieval_count", 0)
            ) + len(hints)
            skill_stats["memory_snapshot_hash"] = plan.snapshot_hash
            skill_stats["memory_injection_receipts"] = [
                receipt.model_dump(mode="json") for receipt in plan.receipts
            ]
            skill_stats["memory_injection_receipt_status"] = "prepared_not_injected"
            skill_stats["memory_full_grader_validated"] = False
            return hints

        test_output = ""
        for action in reversed(previous_actions):
            test_result = action.get("test_result")
            if isinstance(test_result, dict):
                stdout = str(test_result.get("stdout", ""))
                stderr = str(test_result.get("stderr", ""))
                test_output = stdout + stderr
                break
        baseline = self.memory_retriever.select(
            task,
            repo_fingerprint,
            max_hints=3,
            test_output=test_output,
        )
        if policy is None:
            skill_stats["memory_candidate_count"] = (
                int(skill_stats.get("memory_candidate_count", 0)) + baseline.candidate_count
            )
            skill_stats["memory_injected_count"] = (
                int(skill_stats.get("memory_injected_count", 0)) + baseline.injected_count
            )
            skill_stats["memory_retrieval_count"] = (
                int(skill_stats.get("memory_retrieval_count", 0)) + baseline.injected_count
            )
            return list(baseline.injected)
        routed = self.memory_retriever.select(
            task,
            repo_fingerprint,
            max_hints=policy.max_memory_hints,
            repo_profile_only=policy.memory_repo_profile_only,
            exclude_episodic_failures=policy.exclude_episodic_failures,
            procedural_only=policy.procedural_only,
            test_output=test_output,
            exclude_repo_profile=policy.exclude_repo_profile,
        )
        hints, suppressed = apply_memory_policy(routed, policy)
        skill_stats["memory_suppressed_by_policy"] = (
            int(skill_stats.get("memory_suppressed_by_policy", 0))
            + int(max(0, baseline.injected_count - len(hints)))
            + suppressed
        )
        skill_stats["memory_candidate_count"] = (
            int(skill_stats.get("memory_candidate_count", 0)) + baseline.candidate_count
        )
        skill_stats["memory_injected_count"] = int(
            skill_stats.get("memory_injected_count", 0)
        ) + len(hints)
        skill_stats["memory_retrieval_count"] = int(
            skill_stats.get("memory_retrieval_count", 0)
        ) + len(hints)
        ids = set(skill_stats.get("memory_source_task_ids", []))
        ids.update(str(h.get("source_task_id", "")) for h in hints if h.get("source_task_id"))
        skill_stats["memory_source_task_ids"] = sorted(ids)
        return hints

    def _select_skills(
        self,
        task: TaskSpec,
        previous_actions: list[dict],
        adapter: WorkspaceAdapter,
        skill_stats: dict[str, object],
        patch_policy=None,
    ):
        evidence = self._build_skill_evidence(task, previous_actions, adapter)
        loaded = self.skill_registry.all()
        retrieved = self.skill_retriever.retrieve(task, loaded, top_k=5)
        selection = self.skill_validator.validate(task, retrieved, evidence)
        policy = patch_policy if patch_policy is not None else self._augmentation_policy
        selection, suppressed = apply_skill_policy(selection, policy)
        if suppressed:
            skill_stats["skill_suppressed_by_policy"] = (
                int(skill_stats.get("skill_suppressed_by_policy", 0)) + suppressed
            )
        self._record_skill_selection(skill_stats, selection)
        return selection

    @staticmethod
    def _build_skill_evidence(
        task: TaskSpec,
        previous_actions: list[dict],
        adapter: WorkspaceAdapter,
    ) -> SkillEvidenceContext:
        test_output = ""
        locator_matches: list[str] = []
        for action in previous_actions:
            if "test_result" in action:
                test_output = str(action["test_result"].get("stderr", "")) + str(
                    action["test_result"].get("stdout", "")
                )
            matches = action.get("matches")
            if isinstance(matches, list):
                locator_matches.extend(str(path) for path in matches)
        repo_files = adapter.list_files("**/*.py")[:80]
        return SkillEvidenceContext(
            issue=task.issue,
            tags=task.tags,
            expected_files=task.expected_files,
            test_output=test_output,
            locator_matches=locator_matches,
            repo_files=repo_files,
        )

    @staticmethod
    def _record_skill_selection(skill_stats: dict[str, object], selection) -> None:
        skill_stats["skill_retrieved_count"] = int(skill_stats.get("skill_retrieved_count", 0)) + (
            selection.retrieved_count
        )
        skill_stats["skill_validated_count"] = (
            int(skill_stats.get("skill_validated_count", 0)) + selection.validated_count
        )
        skill_stats["skill_candidate_count"] = (
            int(skill_stats.get("skill_candidate_count", 0)) + selection.candidate_count
        )
        skill_stats["skill_injected_count"] = (
            int(skill_stats.get("skill_injected_count", 0)) + selection.injected_count
        )
        skill_stats["skill_gated_count"] = int(skill_stats.get("skill_gated_count", 0)) + (
            selection.gated_count
        )
        if selection.injected_count > 0:
            skill_stats["skill_used_in_run"] = 1
        ids = set(skill_stats.get("skill_ids_used", []))
        ids.update(skill.id for skill in selection.selected)
        skill_stats["skill_ids_used"] = sorted(ids)

    def _bind_adapter(self, workspace: Path) -> WorkspaceAdapter:
        if self.adapter_kind == "fake":
            from reposkill_agent.adapters.fake_adapter import FakeAdapter

            return FakeAdapter(
                workspace,
                scripted_fixes=SCRIPTED_FIXES,
                allow_prefix_scripted_fixes=self.allow_prefix_scripted_fixes,
            )
        return OpenHandsAdapter(workspace)

    def _build_role_agents(self) -> dict[str, RoleAgent]:
        developer: RoleAgent
        if self.developer_mode == "llm":
            if self.model_client is None:
                raise ValueError("developer_mode=llm requires model_client")
            developer = LLMDeveloperAgent(
                self.model_client,
                max_calls_per_task=self.max_llm_calls_per_task,
                call_state=self.llm_call_state,
            )
        else:
            developer = DeveloperAgent()
        return {
            "manager": ManagerAgent(),
            "locator": LocatorAgent(),
            "developer": developer,
            "qa": QAAgent(),
        }

    @staticmethod
    def _merge_llm_metrics(skill_stats: dict[str, object], llm_metrics: object) -> None:
        if not isinstance(llm_metrics, dict):
            return
        for key in (
            "llm_call_count",
            "llm_parse_error_count",
            "llm_patch_rejected_count",
            "llm_patch_applied_count",
            "llm_prompt_tokens_estimate",
            "llm_completion_tokens_estimate",
            "llm_wall_time_ms",
            "llm_parse_repair_attempt_total",
            "llm_parse_repair_success_total",
        ):
            if key in llm_metrics:
                skill_stats[key] = int(skill_stats.get(key, 0)) + int(llm_metrics[key])
        if llm_metrics.get("llm_error_type"):
            skill_stats["llm_error_type"] = llm_metrics["llm_error_type"]

    def _single_graph_execute(
        self,
        *,
        node: TaskNode,
        adapter: WorkspaceAdapter,
        task: TaskSpec,
        replan_count: int = 0,
        previous_actions: list[dict] | None = None,
        memory_hints: list[dict] | None = None,
        skill_stats: dict[str, object] | None = None,
        expanded_paths: list[str] | None = None,
        patch_policy=None,
    ) -> tuple[bool, dict]:
        paths = expanded_paths or []
        if node.id == "inspect":
            files = adapter.list_files("**/*.py")
            return True, {"matched_files": files[:20], "count": len(files)}
        if node.id == "locate":
            locator = LocatorAgent()
            context = AgentContext(
                task=task,
                node=node,
                replan_count=replan_count,
                previous_actions=previous_actions or [],
                memory_hints=memory_hints or [],
                expanded_paths=paths,
            )
            result = locator.run(context, adapter)
            return result.success, result.payload
        if node.id == "patch":
            active_skills: list[dict] = []
            if self.use_skills and skill_stats is not None:
                selection = self._select_skills(
                    task,
                    previous_actions or [],
                    adapter,
                    skill_stats,
                    patch_policy=patch_policy,
                )
                active_skills = [skill.model_dump() for skill in selection.selected]
            if self.developer_mode == "llm":
                developer = self.role_agents["developer"]
                context = AgentContext(
                    task=task,
                    node=node,
                    replan_count=replan_count,
                    previous_actions=previous_actions or [],
                    memory_hints=memory_hints or [],
                    active_skills=active_skills,
                    expanded_paths=paths,
                )
                result = developer.run(context, adapter)
                if skill_stats is not None:
                    self._merge_llm_metrics(skill_stats, result.payload.get("llm_metrics"))
                return result.success, result.payload
            patch_results = []
            if self.adapter_kind == "fake":
                from reposkill_agent.adapters.fake_adapter import FakeAdapter

                if isinstance(adapter, FakeAdapter):
                    patch_results = adapter.apply_scripted_fix(task.id)
            else:
                fixes = SCRIPTED_FIXES.get(task.id, [])
                for fix in fixes:
                    patch_results.append(adapter.apply_patch(fix))
            serialized = [item.model_dump() for item in patch_results]
            return bool(serialized), {
                "patches": serialized,
                "patch_strategy": "single_graph_scripted",
            }
        if node.id == "test":
            test_result = adapter.run_tests(task.test_command)
            return test_result.passed, {
                "test_result": test_result.model_dump(),
                "test_result_obj": test_result,
            }
        if node.id == "summarize":
            return True, {"summary": f"task={task.id} complete"}
        return False, {"error": f"unknown node id: {node.id}"}

    def _node_role(self, node_owner: str) -> str:
        if self.execution_mode == "single_graph":
            return "planner_agent"
        return node_owner

    @staticmethod
    def _emit_node(
        trace: TraceWriter,
        node: TaskNode,
        event_type: str,
        status: str,
        payload: dict | None = None,
        agent_role: str | None = None,
    ) -> None:
        out = {"node_id": node.id, "owner": node.owner, "status": status}
        if payload:
            out.update(payload)
        trace.emit(event_type, out, agent_role=agent_role or node.owner)
