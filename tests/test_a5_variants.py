import json

import pytest

from reposkill_agent.evidence.models import EvidenceState
from reposkill_agent.experiments.contracts import (
    DatasetManifest,
    ExperimentContract,
    MemoryBuildManifest,
    model_hash,
)
from reposkill_agent.experiments.offline import NOW, fixture_inputs
from reposkill_agent.experiments.variants import select_variant
from reposkill_agent.protocol.public import decode_public_task, digest


def decisions(index=1, empty=False):
    c, d, m, e, tasks, facts, _ = fixture_inputs()
    if empty:
        m = e
        c = ExperimentContract(**{**c.model_dump(), "memory_hash": model_hash(m)})
    task = tasks[index]
    return [
        select_variant(
            task,
            EvidenceState(repo_revision=task.repo_ref.revision),
            facts[index],
            c,
            d,
            m,
            v,
            now=NOW,
            decision_id="same-public-decision",
        )
        for v in c.variants
    ]


def test_no_augmentation_and_empty_pool_do_not_invent_candidates():
    assert not decisions()[0].items
    assert all(not d.items for d in decisions(empty=True))
    assert all(not d.context_candidates() for d in decisions(empty=True))


def test_same_history_ranking_quota_and_b2_b3_representation():
    _, b1, b2, b3 = decisions()
    assert len({d.profile_hash for d in (b1, b2, b3)}) == 1
    assert len({d.history_hash for d in (b1, b2, b3)}) == 1
    assert [(i.score, i.source_hash) for i in b1.items] == [
        (i.score, i.source_hash) for i in b2.items
    ]
    assert b1.items[0].text != b2.items[0].text
    assert b2.items[0].text == b3.items[0].text
    assert b1.items[0].selected and b2.items[0].selected and b3.items[0].selected
    assert b2.items[0].validity == "not_checked"
    assert b3.items[0].validity == "valid"


@pytest.mark.parametrize("index, validity", [(2, "invalid"), (3, "unknown")])
def test_b3_stale_unknown_rejection_is_only_ablation_difference(index, validity):
    _, b1, b2, b3 = decisions(index=index)
    assert b1.items[0].selected and b2.items[0].selected
    assert not b3.items[0].selected
    assert b2.items[0].text == b3.items[0].text
    assert b3.items[0].validity == validity
    assert "validity_" + validity in b3.items[0].reasons
    assert b3.items[0].validity_reasons


def test_no_labels_or_evaluator_in_public_input_index_prompt():
    c, d, m, _, tasks, facts, _ = fixture_inputs()
    task, _ = decode_public_task(tasks[1].model_dump(mode="json"))
    evidence = EvidenceState(repo_revision=task.repo_ref.revision)
    before = select_variant(task, evidence, facts[1], c, d, m, "B3", now=NOW, decision_id="d")
    for sentinel in ("ORACLE_SENTINEL_A", "ORACLE_SENTINEL_B"):
        private_evaluation = {"gold_patch": sentinel, "tags": [sentinel]}
        assert private_evaluation  # Deliberately never passed to the policy.
        after = select_variant(task, evidence, facts[1], c, d, m, "B3", now=NOW, decision_id="d")
        assert before == after
        public = json.dumps(
            [task.model_dump(mode="json"), m.history[0].raw_text, after.context_candidates()]
        )
        assert sentinel not in public
    with pytest.raises(ValueError):
        decode_public_task({**task.model_dump(mode="json"), "tags": ["parser"]})


def test_changed_task_budget_and_unfrozen_dataset_refused():
    c, d, m, _, tasks, facts, _ = fixture_inputs()
    with pytest.raises(ValueError, match="contract_manifest"):
        select_variant(
            tasks[1],
            EvidenceState(repo_revision=tasks[1].repo_ref.revision),
            facts[1],
            c.model_copy(update={"memory_hash": "0" * 64}),
            d,
            m,
            "B0",
            now=NOW,
            decision_id="d",
        )


def expanded_pool(procedures, *, conflict=False):
    c, d, m, _, tasks, facts, _ = fixture_inputs()
    history, sources = [], []
    entries = [e.model_dump() for e in d.entries if e.split != "memory_build"]
    for n, procedure in enumerate(procedures):
        item = m.history[0].model_dump()
        raw = json.loads(item["raw_text"])
        raw["failure_notes"] = [f"Public observation {n}"]
        item["raw_text"] = json.dumps(raw)
        src = item["source"]
        src["task_id"] = f"history-{n}"
        src["artifact"].update(
            sha256=digest(item["raw_text"]), size_bytes=len(item["raw_text"].encode())
        )
        item["record"].update(
            memory_id=f"record-{n}",
            procedure=procedure,
            content_hash=digest(procedure),
            sources=(src,),
            conflict_group="conflict" if conflict else None,
        )
        sources.append(src)
        history.append(item)
        entry = d.entries[-1].model_dump()
        entry.update(task_id=src["task_id"], artifact_hash=src["artifact"]["sha256"])
        entries.append(entry)
    dataset = DatasetManifest(**{**d.model_dump(), "entries": entries})
    memory = MemoryBuildManifest(
        **{
            **m.model_dump(),
            "dataset_hash": model_hash(dataset),
            "history": history,
            "policy": {**m.policy.model_dump(), "allowed_sources": sources},
        }
    )
    contract = c.model_copy(
        update={"dataset_hash": model_hash(dataset), "memory_hash": model_hash(memory)}
    )
    return [
        select_variant(
            tasks[1],
            EvidenceState(repo_revision=tasks[1].repo_ref.revision),
            facts[1],
            contract,
            dataset,
            memory,
            variant,
            now=NOW,
            decision_id="d",
        )
        for variant in ("B1", "B2", "B3")
    ]


def test_shared_candidate_window_and_injection_count_limit():
    variants = expanded_pool([f"Inspect parser route {n}" for n in range(5)])
    assert all(len(v.items) == 3 for v in variants)
    assert all(sum(c.selected for c in v.items) == 2 for v in variants)
    assert len({tuple(c.source_hash for c in v.items) for v in variants}) == 1


def test_multibyte_quota_rejects_whole_candidate_without_truncating():
    _, b2, b3 = expanded_pool(["解析配置" * 500])
    for result in (b2, b3):
        item = result.items[0]
        assert len(item.text) < 4096 < item.bytes
        assert item.bytes == len(item.text.encode())
        assert not item.selected and "injection_quota" in item.reasons
        assert not result.context_candidates()


def test_duplicate_and_conflict_gates_are_common_to_augmented_variants():
    assert all(
        sum(c.selected for c in v.items) == 1
        for v in expanded_pool(["Inspect parser", "Inspect parser"])
    )
    for v in expanded_pool(["Inspect parser input", "Inspect parser output"], conflict=True):
        assert all(not c.selected and "unresolved_conflict" in c.reasons for c in v.items)


def test_opaque_task_identity_and_seed_do_not_affect_selection():
    c, d, m, _, tasks, facts, _ = fixture_inputs()
    task = tasks[1].model_copy(update={"task_id": "opaque-917", "workspace_id": "random-456"})
    entries = [e.model_dump() for e in d.entries]
    entries[1].update(task_id=task.task_id, public_task_hash=model_hash(task))
    dataset = DatasetManifest(**{**d.model_dump(), "entries": entries})
    policy = m.policy.model_copy(
        update={
            "target_task_ids": tuple(
                task.task_id if t == tasks[1].task_id else t for t in m.policy.target_task_ids
            )
        }
    )
    memory = m.model_copy(update={"dataset_hash": model_hash(dataset), "policy": policy})
    contract = c.model_copy(
        update={
            "dataset_hash": model_hash(dataset),
            "memory_hash": model_hash(memory),
            "seeds": (1729,),
        }
    )
    after = select_variant(
        task,
        EvidenceState(repo_revision=task.repo_ref.revision),
        facts[1],
        contract,
        dataset,
        memory,
        "B3",
        now=NOW,
        decision_id="same-public-decision",
    )
    assert after.items == decisions()[3].items
