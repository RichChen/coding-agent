import json

import pytest

from reposkill_agent.experiments.contracts import (
    DatasetManifest,
    ExperimentContract,
    HistoryItem,
    MemoryBuildManifest,
    bind_task,
    model_hash,
    pilot_blockers,
    validate_manifests,
)
from reposkill_agent.experiments.offline import NOW, fixture_inputs
from reposkill_agent.memory.records import SourceRef
from reposkill_agent.memory.source_manifest import SourcePolicy
from reposkill_agent.protocol.public import digest


def test_frozen_contract_and_empty_snapshot_are_auditable():
    contract, dataset, memory, empty, tasks, _, _ = fixture_inputs()
    validate_manifests(dataset, memory)
    validate_manifests(dataset, empty)
    assert contract.dataset_hash == model_hash(dataset)
    assert contract.memory_hash == model_hash(memory)
    assert all(bind_task(t, dataset).split == "dev" for t in tasks)
    assert memory.history[0].record.build_usage.method == "human-authored"


@pytest.mark.parametrize("key", ["artifact_hash", "duplicate_group", "task_id", "reviewed"])
def test_split_contamination_and_missing_review_rejected(key):
    _, dataset, _, _, _, _, _ = fixture_inputs()
    data = dataset.model_dump()
    data["entries"] = list(data["entries"])
    data["entries"][0][key] = False if key == "reviewed" else data["entries"][-1][key]
    with pytest.raises(ValueError):
        DatasetManifest(**data)


def test_repo_disjoint_cannot_be_claimed_for_same_repo_fixture():
    _, dataset, *_ = fixture_inputs()
    with pytest.raises(ValueError, match="cross_split_repo_id"):
        DatasetManifest(**{**dataset.model_dump(), "split_policy": "repo_disjoint"})


def test_exposed_dev_cannot_be_relabelled_heldout():
    _, dataset, *_ = fixture_inputs()
    data = dataset.model_dump()
    data["entries"][0]["split"] = "heldout"
    with pytest.raises(ValueError, match="development_exposure"):
        DatasetManifest(**data)


@pytest.mark.parametrize("change", ["source_split", "source_time", "source_mode", "pool", "hash"])
def test_build_manifest_fails_closed(change):
    _, dataset, memory, _, _, _, _ = fixture_inputs()
    data = memory.model_dump()
    if change == "hash":
        data["dataset_hash"] = digest("other")
    elif change == "pool":
        data["policy"]["allowed_sources"] = ()
    else:
        source = data["history"][0]["source"]
        if change == "source_split":
            source["split"] = "heldout"
        elif change == "source_time":
            source["occurred_at"] = NOW
        else:
            source["protocol_mode"] = "diagnostic_oracle"
        data["history"][0]["record"]["sources"] = (source,)
        data["policy"]["allowed_sources"] = (source,)
    with pytest.raises(ValueError):
        validate_manifests(dataset, MemoryBuildManifest(**data))


def test_duplicate_artifact_and_missing_target_rejected():
    _, dataset, memory, *_ = fixture_inputs()
    duplicate = memory.model_copy(update={"history": memory.history * 2})
    with pytest.raises(ValueError, match="duplicate_history"):
        validate_manifests(dataset, duplicate)
    policy = SourcePolicy(**{**memory.policy.model_dump(), "target_task_ids": ()})
    with pytest.raises(ValueError, match="target_set"):
        validate_manifests(dataset, memory.model_copy(update={"policy": policy}))


def test_oracle_fields_cannot_enter_index_even_with_updated_hash():
    _, _, memory, *_ = fixture_inputs()
    h = memory.history[0]
    raw = json.loads(h.raw_text)
    raw["gold_patch"] = "ORACLE_SENTINEL"
    text = json.dumps(raw)
    src_data = h.source.model_dump()
    src_data["artifact"].update(sha256=digest(text), size_bytes=len(text.encode()))
    src = SourceRef(**src_data)
    with pytest.raises(ValueError):
        HistoryItem(source=src, raw_text=text, record=h.record)


def test_pilot_templates_block_paid_runs_and_keep_repeats_fixed():
    for size in (12, 20):
        c = ExperimentContract(
            experiment_id=f"pilot-{size}",
            mode="pilot_template",
            target_count=size,
            repeats=3,
            seeds=(42, 43, 44),
        )
        assert "experiment_cost_cap" in pilot_blockers(c)
        assert "dataset_hash" in pilot_blockers(c)
    with pytest.raises(ValueError, match="profile_change"):
        ExperimentContract(
            experiment_id="bad",
            mode="offline_smoke",
            target_count=4,
            profile={"model_calls": 1},
        )
