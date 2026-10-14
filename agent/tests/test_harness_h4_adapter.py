"""Single-repository H4 wire fixtures; never imports/runs the other repository."""

import asyncio
import copy
import inspect
import json

import pytest

from reposkill_agent.eval.h4_fixture import SEED, H3EvaluationSpec, prepare_h4_fixture
from reposkill_agent.integrations.harness_h4 import (
    MAX_POLICY_BYTES,
    RepoSkillH4Plugin,
    harness_public_task,
)
from reposkill_agent.protocol.public import BoundaryError, PublicTask, canonical, digest
from tests.upgrade_helpers import facts, policy, task, validated


def policy_input(**updates):
    t = task()
    data = dict(
        schema_version="0.1",
        task={"task_id": t.task_id, "issue_text": t.issue_text},
        observations=[dict(role="user", sha256=digest("public issue"))],
        repo_revision=t.repo_ref.revision,
        budget={},
        state={},
    )
    data.update(updates)
    return data


def decide(plugin=None, data=None):
    plugin = plugin or RepoSkillH4Plugin(task(), ("config.py",))
    return asyncio.run(plugin.decide(policy_input() if data is None else data))


def assert_h4_decision(result):
    # Shape from H4 plugin.py validate_decision, not a runtime simulation.
    assert set(result) == {"schema_version", "candidates", "state", "events", "action_proposals"}
    assert result["schema_version"] == "0.1"
    assert isinstance(result["state"], dict)
    for key in ("candidates", "events", "action_proposals"):
        assert isinstance(result[key], list)
    assert len(json.dumps(result, ensure_ascii=False, allow_nan=False).encode()) <= MAX_POLICY_BYTES
    assert len({c["id"] for c in result["candidates"]}) == len(result["candidates"])
    for candidate in result["candidates"]:
        assert all(
            isinstance(candidate[k], str) and candidate[k]
            for k in ("id", "text", "source", "reason")
        )
        assert type(candidate["valid"]) is bool


def test_async_contract_no_side_effects_and_noop():
    assert inspect.iscoroutinefunction(RepoSkillH4Plugin.decide)
    raw = policy_input()
    original = copy.deepcopy(raw)
    result = decide(data=raw)
    assert raw == original
    assert_h4_decision(result)
    assert result["action_proposals"][0]["tool"] == "read"
    assert result["action_proposals"][0]["path"] == "config.py"
    assert result["state"]["strategy"]["evidence_state"]["observations"] == []
    assert result["events"][0]["external_model_calls"] == 0
    assert result["events"][0]["tool_calls_executed"] == 0
    assert result["events"][0]["injection_status"] == "await_host_record"
    off = decide(RepoSkillH4Plugin(task(), ("config.py",), enabled=False))
    assert off == dict(
        schema_version="0.1", candidates=[], state={}, events=[], action_proposals=[]
    )


def test_h3_task_wrapper_and_direct_projection_match_minimal_input():
    public = harness_public_task(task())
    wrapper = {"task_id": task().task_id, "issue_text": json.dumps(public)}
    assert decide(data=policy_input(task=wrapper)) == decide()
    assert decide(data=policy_input(task=public)) == decide()


def test_restore_new_instance_and_new_run_without_replaying_proposals():
    first = decide()
    restored_input = policy_input(state=json.loads(json.dumps(first["state"])))
    second = decide(data=restored_input)
    assert second["state"]["calls"] == 2
    first_ids = {p["proposal_id"] for p in first["action_proposals"]}
    second_ids = {p["proposal_id"] for p in second["action_proposals"]}
    assert not first_ids & second_ids
    assert decide(data=policy_input(state=second["state"]))["action_proposals"] == []
    assert second["state"]["strategy"]["proposal_ids"]
    assert second["state"]["strategy"]["receipt_cursor"] is None
    assert second == decide(data=restored_input)
    assert decide() == first


@pytest.mark.parametrize("change", ["tree", "memory", "evidence_revision", "receipt", "major"])
def test_checkpoint_cannot_resume_changed_binding_or_invent_evidence(change):
    state = decide()["state"]
    plugin = RepoSkillH4Plugin(task(), ("config.py",))
    if change == "tree":
        plugin = RepoSkillH4Plugin(task(), ("other.py",))
    elif change == "memory":
        state["strategy"]["memory_snapshot_id"] = digest("other")
    elif change == "evidence_revision":
        state["strategy"]["evidence_state"]["repo_revision"] = "v2"
    elif change == "receipt":
        state["strategy"]["receipt_cursor"] = "not-supplied-by-h4"
    else:
        state["schema_version"] = "1.0"
    with pytest.raises(BoundaryError, match="invalid_h4_checkpoint"):
        decide(plugin, policy_input(state=state))


@pytest.mark.parametrize(
    "field",
    [
        "gold_patch",
        "hidden_tests",
        "expected_files",
        "tags",
        "category",
        "future_trajectory",
        "evaluation_spec",
        "answer",
        "expected",
        "oracle",
        "future_solution",
    ],
)
def test_private_fields_rejected_even_in_ignored_extensions(field):
    raw = policy_input(schema_version="0.2", extension={field: "PRIVATE_CANARY"})
    with pytest.raises(BoundaryError) as error:
        decide(data=raw)
    assert "PRIVATE_CANARY" not in str(error.value)


def test_private_fields_in_h3_serialized_task_are_rejected():
    public = harness_public_task(task())
    public["expected_files"] = ["PRIVATE_CANARY.py"]
    with pytest.raises(BoundaryError) as error:
        decide(
            data=policy_input(task={"task_id": task().task_id, "issue_text": json.dumps(public)})
        )
    assert "PRIVATE_CANARY" not in str(error.value)


@pytest.mark.parametrize(
    "updates",
    [
        {"schema_version": "1.0"},
        {"repo_revision": None},
        {"repo_revision": "changed"},
        {"observations": [{"role": "tool", "sha256": "not-a-hash"}]},
        {"budget": {"cost": float("nan")}},
        {"extra": "unknown"},
        {"budget": {"value": "x" * MAX_POLICY_BYTES}},
        {"task": {"task_id": "other", "issue_text": "same"}},
    ],
)
def test_bad_wire_inputs_fail_closed(updates):
    with pytest.raises(BoundaryError):
        decide(data=policy_input(**updates))


def test_minor_extensions_do_not_influence_decision_or_echo_values():
    result = decide(data=policy_input(schema_version="0.2", extension="PRIVATE_CANARY"))
    assert result == decide()
    assert "PRIVATE_CANARY" not in json.dumps(result)


def test_hashes_are_not_observation_bodies_and_memory_is_withheld_after_tools():
    plugin = RepoSkillH4Plugin(
        task(),
        ("config.py",),
        records=(validated(),),
        facts=facts(),
        source_policy=policy(),
    )
    first = decide(plugin)
    assert any(c["source"].startswith("reposkill:memory:") for c in first["candidates"])
    second = decide(
        plugin,
        policy_input(
            state=first["state"],
            observations=[dict(role="tool", sha256=digest("unknown result"))],
        ),
    )
    assert not any(c["source"].startswith("reposkill:memory:") for c in second["candidates"])
    assert second["events"][0]["memory_status"] == "withheld_after_tool_history"
    assert second["state"]["strategy"]["evidence_state"]["observations"] == []
    third = decide(plugin, policy_input(state=second["state"]))
    assert third["events"][0]["memory_status"] == "withheld_after_tool_history"


def test_invalid_memory_not_sent_and_snapshot_changes_reject_restore():
    f = facts(facts=())
    plugin = RepoSkillH4Plugin(
        task(),
        ("config.py",),
        records=(validated(),),
        facts=f,
        source_policy=policy(),
    )
    result = decide(plugin)
    assert not any(c["source"].startswith("reposkill:memory:") for c in result["candidates"])
    assert "validity_unknown" in result["events"][0]["memory_items"][0]["reasons"]
    with pytest.raises(BoundaryError, match="invalid_h4_checkpoint"):
        decide(data=policy_input(state=result["state"]))


def test_cooperative_cancellation_does_not_commit_plugin_state():
    async def run():
        plugin = RepoSkillH4Plugin(task(), ("config.py",))
        pending = asyncio.create_task(plugin.decide(policy_input()))
        await asyncio.sleep(0)
        pending.cancel()
        with pytest.raises(asyncio.CancelledError):
            await pending
        result = await plugin.decide(policy_input())
        assert result["state"]["calls"] == 1

    asyncio.run(run())


def test_adapter_has_no_runtime_model_network_or_private_evaluation_import():
    import ast

    import reposkill_agent.integrations.harness_h4 as module

    tree = ast.parse(inspect.getsource(module))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    assert not any(
        name.startswith(
            (
                "src.",
                "http",
                "socket",
                "subprocess",
                "reposkill_agent.llm",
                "reposkill_agent.adapters",
                "reposkill_agent.eval",
            )
        )
        for name in imported
    )


def test_prepared_task_is_frozen_and_private_canary_never_reaches_plugin(tmp_path):
    output = tmp_path / "prepared"
    image = "fixture@sha256:" + "a" * 64  # Schema test only; never claims an available image.
    manifest = prepare_h4_fixture(output, image=image)
    assert manifest["external_model_calls"] == 0 and manifest["repair_success"] is None
    assert not manifest["real_api_ready"]
    private = json.loads((output / "private/evaluation-spec.json").read_text())
    spec = H3EvaluationSpec.model_validate(private)
    assert len(spec.cases) == 4
    t = PublicTask.model_validate_json((output / "agent-public-task.json").read_text())
    public = json.loads((output / "public-task.json").read_text())
    assert public == harness_public_task(t)
    assert spec.base_hash == digest(canonical({p: digest(s) for p, s in SEED.items()}))
    workspace_files = {
        p.relative_to(output / "public-workspace").as_posix()
        for p in (output / "public-workspace").rglob("*")
        if p.is_file()
    }
    assert workspace_files == set(SEED)
    for name, sha in manifest["artifacts"].items():
        assert digest((output / name).read_bytes()) == sha
    private_strings = ("PRIVATE_H4_CANARY_7f2c", '"expected":', "private/evaluation-spec.json")
    for path in list((output / "public-workspace").rglob("*.py")) + list(
        (output / "fixture").glob("*.json")
    ):
        content = path.read_text()
        assert not any(s in content for s in private_strings)
    raw = json.loads((output / "fixture/policy-input.json").read_text())
    messages = json.loads((output / "fixture/raw-messages.json").read_text())
    assert raw["observations"][0]["sha256"] == digest(canonical(messages[0]))
    before = decide(RepoSkillH4Plugin(t, tuple(SEED)), raw)
    # Changing private expected answers and identity canaries cannot affect the
    # plugin: it has neither a path/resolver nor a parameter for this object.
    private["cases"][0]["expected"] = {"SECOND_PRIVATE_CANARY": "changed"}
    assert decide(RepoSkillH4Plugin(t, tuple(SEED)), raw) == before
    with pytest.raises(FileExistsError):
        prepare_h4_fixture(output, image=image)


def test_public_seed_reproduces_failure_without_private_grader():
    scope = {}
    exec(compile(SEED["settings.py"], "public-fixture", "exec"), scope)
    assert scope["parse_settings"]("a=1") == {"a": "1"}
    with pytest.raises(ValueError):
        scope["parse_settings"]("name=demo\n\n")
