"""Frozen E-A1 contracts and fail-closed provenance checks."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import AwareDatetime, Field, model_validator

from reposkill_agent.integrations.harness_h4 import wire_data
from reposkill_agent.memory.builder import PublicTrajectory
from reposkill_agent.memory.records import MemoryRecord, SourceRef, contains_secret
from reposkill_agent.memory.source_manifest import SourcePolicy, validate_build_manifest
from reposkill_agent.protocol.public import (
    Digest,
    PublicTask,
    StrictModel,
    Versioned,
    canonical,
    digest,
)

Variant = Literal["B0", "B1", "B2", "B3"]
VARIANTS = ("B0", "B1", "B2", "B3")


def model_hash(model) -> str:
    return digest(canonical(model.model_dump(mode="json")))


class CommonProfile(StrictModel):
    loop: Literal["harness-react"] = "harness-react"
    context: Literal["none"] = "none"
    backend: Literal["docker_linux"] = "docker_linux"
    tools: tuple[str, ...] = ("read_file", "list_dir", "edit_file", "run_command")
    retry_limit: int = 1
    model_calls: int = 6
    input_tokens: int = 48000
    output_tokens: int = 12000
    wall_seconds: int = 600
    tool_calls: int = 30
    candidate_limit: int = 3
    injection_limit: int = 2
    injection_bytes: int = 4096


class ExperimentContract(Versioned):
    experiment_id: str
    protocol: Literal["E-A1"] = "E-A1"
    mode: Literal["offline_smoke", "pilot_template"]
    protocol_mode: Literal["realistic"] = "realistic"
    variants: tuple[Variant, ...] = VARIANTS
    profile: CommonProfile = Field(default_factory=CommonProfile)
    repeats: int = Field(default=1, ge=1)
    seeds: tuple[int, ...] = (42,)
    target_count: int = Field(ge=1)
    memory_mode: Literal["cold_frozen"] = "cold_frozen"
    ranking: Literal["lexical_set_overlap_v1"] = "lexical_set_overlap_v1"
    primary_denominator: Literal["all_assigned_first_attempt"] = "all_assigned_first_attempt"
    model: str | None = None
    model_snapshot: str | None = None
    temperature: float = 0
    provider_seed_supported: bool = False
    currency: str | None = None
    run_cost_cap: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    experiment_cost_cap: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    dataset_hash: Digest | None = None
    memory_hash: Digest | None = None

    @model_validator(mode="after")
    def fixed(self):
        if self.variants != VARIANTS or len(self.seeds) != self.repeats:
            raise ValueError("invalid_variant_or_repeat_contract")
        if self.profile != CommonProfile():
            raise ValueError("profile_change_requires_new_contract")
        if self.mode == "pilot_template" and (
            self.target_count not in (12, 20) or self.repeats != 3
        ):
            raise ValueError("pilot_shape_mismatch")
        return self


class DataEntry(StrictModel):
    task_id: str
    repo_id: str
    revision: str
    source_type: Literal["synthetic", "public_issue", "public_trajectory"]
    origin: str = Field(min_length=1)
    license: str = Field(min_length=1)
    split: Literal["memory_build", "dev", "heldout"]
    occurred_at: AwareDatetime
    time_basis: Literal["synthetic_version_order", "documented_timestamp"]
    artifact_hash: Digest
    duplicate_group: str = Field(min_length=1)
    public_task_hash: Digest | None = None
    public_issue_hash: Digest | None = None
    development_exposure: tuple[str, ...] = ()
    review_evidence: str = Field(min_length=1)
    reviewed: bool


class DatasetManifest(Versioned):
    dataset_id: str
    split_policy: Literal["same_repo_time", "repo_disjoint"] = "same_repo_time"
    contamination_statement: str = Field(min_length=1)
    entries: tuple[DataEntry, ...]

    @model_validator(mode="after")
    def disjoint(self):
        if len({e.task_id for e in self.entries}) != len(self.entries):
            raise ValueError("duplicate_task_id")
        for entry in self.entries:
            if not entry.reviewed:
                raise ValueError("missing_contamination_review")
            if entry.split == "heldout" and entry.development_exposure:
                raise ValueError("heldout_development_exposure")
            if entry.split != "memory_build" and (
                entry.public_task_hash is None or entry.public_issue_hash is None
            ):
                raise ValueError("missing_public_task_hash")
        fields = ["artifact_hash", "duplicate_group"]
        if self.split_policy == "repo_disjoint":
            fields.append("repo_id")
        for field in fields:
            splits = {}
            for entry in self.entries:
                splits.setdefault(getattr(entry, field), set()).add(entry.split)
            if any(len(values) > 1 for values in splits.values()):
                raise ValueError("cross_split_" + field)
        return self


class HistoryItem(StrictModel):
    source: SourceRef
    raw_text: str
    record: MemoryRecord

    @model_validator(mode="after")
    def bound(self):
        wire_data(json.loads(self.raw_text))
        PublicTrajectory.model_validate_json(self.raw_text)
        if contains_secret(self.raw_text):
            raise ValueError("secret_history")
        if self.source.artifact.sha256 != digest(self.raw_text) or (
            self.source.artifact.size_bytes != len(self.raw_text.encode())
        ):
            raise ValueError("history_bytes_mismatch")
        if self.record.sources != (self.source,):
            raise ValueError("history_record_source_mismatch")
        return self


class MemoryBuildManifest(Versioned):
    build_id: str
    dataset_hash: Digest
    policy: SourcePolicy
    history: tuple[HistoryItem, ...]
    builder: Literal["human-reviewed-structure-v1"] = "human-reviewed-structure-v1"
    freeze_mode: Literal["cold_frozen"] = "cold_frozen"
    build_wall_ms: float = Field(ge=0, allow_inf_nan=False)


def validate_manifests(dataset: DatasetManifest, memory: MemoryBuildManifest) -> None:
    # Revalidate even callers' model_copy objects.
    dataset = DatasetManifest.model_validate(dataset.model_dump())
    memory = MemoryBuildManifest.model_validate(memory.model_dump())
    if memory.dataset_hash != model_hash(dataset):
        raise ValueError("dataset_freeze_mismatch")
    validate_build_manifest(memory.policy)
    entries = {e.task_id: e for e in dataset.entries}
    targets = {e.task_id for e in dataset.entries if e.split != "memory_build"}
    if set(memory.policy.target_task_ids) != targets:
        raise ValueError("policy_target_set_mismatch")
    sources = tuple(h.source for h in memory.history)
    if set(s.model_dump_json() for s in sources) != set(
        s.model_dump_json() for s in memory.policy.allowed_sources
    ):
        raise ValueError("history_pool_mismatch")
    if len({h.source.artifact.sha256 for h in memory.history}) != len(memory.history):
        raise ValueError("duplicate_history_artifact")
    if len({h.record.memory_id for h in memory.history}) != len(memory.history):
        raise ValueError("duplicate_history_record")
    for item in memory.history:
        source = item.source
        entry = entries.get(source.task_id)
        if (
            entry is None
            or entry.split != "memory_build"
            or (
                entry.artifact_hash,
                entry.repo_id,
                entry.revision,
                entry.occurred_at,
                entry.duplicate_group,
            )
            != (
                source.artifact.sha256,
                source.repo_id,
                source.repo_revision,
                source.occurred_at,
                source.duplicate_group,
            )
        ):
            raise ValueError("source_dataset_mismatch")
        if memory.policy.reasons(item.record):
            raise ValueError("inadmissible_build_source")
        for target in dataset.entries:
            if target.split != "memory_build" and source.occurred_at >= target.occurred_at:
                raise ValueError("nonhistorical_source")


def bind_task(task: PublicTask, dataset: DatasetManifest) -> DataEntry:
    if task.protocol_mode != "realistic":
        raise ValueError("realistic_required")
    entry = next((e for e in dataset.entries if e.task_id == task.task_id), None)
    if entry is None or entry.split == "memory_build" or entry.public_task_hash != model_hash(task):
        raise ValueError("task_manifest_mismatch")
    if (entry.repo_id, entry.revision, entry.public_issue_hash) != (
        task.repo_ref.repo_id,
        task.repo_ref.revision,
        digest(task.issue_text),
    ):
        raise ValueError("task_source_mismatch")
    return entry


def require_frozen(contract, dataset, memory):
    ExperimentContract.model_validate(contract.model_dump())
    validate_manifests(dataset, memory)
    if contract.dataset_hash != model_hash(dataset) or contract.memory_hash != model_hash(memory):
        raise ValueError("contract_manifest_mismatch")


def pilot_blockers(contract: ExperimentContract) -> list[str]:
    missing = [
        name
        for name in (
            "model",
            "model_snapshot",
            "currency",
            "run_cost_cap",
            "experiment_cost_cap",
            "dataset_hash",
            "memory_hash",
        )
        if getattr(contract, name) is None
    ]
    return missing + ["price_table_and_host_budget_preflight", "explicit_paid_run_authorization"]
