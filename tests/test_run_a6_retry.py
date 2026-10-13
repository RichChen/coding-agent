import asyncio
import hashlib
import json
import random
from decimal import Decimal

import pytest

from scripts import build_a6_attempts as attempts_lib
from scripts import run_a5_main
from scripts import run_a6_retry as r

REAL = {"mock": False, "profile": "b0-v2", "variant": "B0", "model": {"name": "deepseek-flash", "base_url_host": "api.deepseek.com"}}
PREREG_FIELDS = {"task_id", "repo", "arm", "first", "k", "run_dir", "mock", "status", "solved", "model_calls", "first_edit_step",
                 "cost_cny", "stop_reason", "changed_files", "prompt_sha256", "retry"}


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _base(task_id):
    return "Public issue:\nissue of " + task_id


@pytest.fixture
def world(tmp_path, monkeypatch):
    """Three first attempts on two tasks, their record files, and a prompt builder standing in for build_prompt."""
    records = []
    for task, first in (("pkg__pkg-1", "b0r1"), ("pkg__pkg-1", "b0r3"), ("lib__lib-2", "b0r2")):
        text = "<previous_attempt>\nrecord of " + task + " " + first + "\n</previous_attempt>"
        path = tmp_path / "attempts" / (task + "__" + first + ".txt")
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(text.encode("utf-8"))
        records.append({"task": task, "first": first, "file": "attempts/" + path.name, "sha256": _sha(text),
                        "a5_prompt_sha256": _sha(_base(task))})
    manifest = {"schema": attempts_lib.SCHEMA, "template_sha256": attempts_lib.template_sha256(), "attempts": len(records),
                "tasks": 2, "by_task": {"pkg__pkg-1": ["b0r1", "b0r3"], "lib__lib-2": ["b0r2"]}, "records": records}

    def prompt(task, suffix=None):
        return _base(task["id"]) + ("\n\n" + suffix if suffix else "")

    monkeypatch.setattr(r, "build_prompt", prompt)
    monkeypatch.setattr(r, "PARALLEL", 1)
    prepared = {"pkg__pkg-1": {"id": "pkg__pkg-1"}, "lib__lib-2": {"id": "lib__lib-2"}}
    return {"tmp": tmp_path, "manifest": manifest, "prepared": prepared, "out": tmp_path / "runs",
            "repo_of": {"pkg__pkg-1": "pkg/pkg", "lib__lib-2": "lib/lib"}}


def _events(output, prompt, artifact=False):
    payload = {"messages": [{"role": "system", "content": "system"}, {"role": "user", "content": prompt}]}
    if artifact:
        data = json.dumps(payload).encode("utf-8")
        sha = hashlib.sha256(data).hexdigest()
        (output / "session" / "artifacts").mkdir(parents=True)
        (output / "session" / "artifacts" / sha).write_bytes(data)
        payload = {"artifact_ref": {"path": sha, "sha256": sha}}
    lines = [{"event_type": "run.started", "payload": {}}, {"event_type": "state.saved", "payload": payload}]
    (output / "events.jsonl").write_text("\n".join(json.dumps(line) for line in lines) + "\n", encoding="utf-8")


def _fake_runner(monkeypatch, *, statuses=None, cost="0.1", tamper=None, model=None, artifact=False):
    calls = []

    async def fake(task, profile, output, *, mock, variant, prompt_suffix, retry):
        status = statuses[len(calls)] if statuses else "fail"
        calls.append({"output": output, "suffix": prompt_suffix, "retry": retry, "mock": mock, "variant": variant})
        prompt = _base(task["id"]) + ("\n\n" + prompt_suffix if prompt_suffix else "")
        sent = tamper(prompt, retry) if tamper else prompt
        row = {"task_id": task["id"], **REAL, "mock": mock, "model": model or REAL["model"], "prompt_sha256": _sha(sent), "retry": retry,
               "status": status, "solved": status == "pass", "cost_cny": cost, "model_calls": 3, "first_edit_step": 2,
               "stop_reason": "completed", "changed_files": ["pkg/a.py"]}
        if mock:
            row["model"] = {"name": "mock-model", "base_url_host": None}
        _events(output, sent, artifact=artifact)
        (output / "summary.json").write_text(json.dumps(row), encoding="utf-8")
        return row

    monkeypatch.setattr(r, "run_task", fake)
    return calls


def _run(world, slots=None, *, mock=False):
    manifest = world["manifest"]
    expected = r.expected_prompts(manifest, world["prepared"], world["tmp"])
    slots = slots if slots is not None else r.slot_queue(manifest["records"])
    return asyncio.run(r.run_slots(slots, mock=mock, out_root=world["out"], manifest=manifest, expected=expected,
                                   prepared=world["prepared"], attempts_sha256="a" * 64, label="test", record_root=world["tmp"]))


def test_constants_follow_the_plan():
    assert (r.SEED, r.TOTAL_CAP, r.PARALLEL, r.EXPECTED_SLOTS) == (20261013, Decimal("210"), run_a5_main.PARALLEL, 318)
    assert r.PARALLEL == 3 and r.PROFILE.name == "b0-v2.yaml"
    assert r.out_root_for(False).name == "a6-retry" and r.out_root_for(True).name == "a6-retry-mock"
    assert r.runs_path_for(True) != r.runs_path_for(False)


def test_queue_is_the_sorted_slots_shuffled_with_the_seed(world):
    records = world["manifest"]["records"]
    queue = r.slot_queue(records)
    expected = sorted((row["task"], arm, row["first"], k) for row in records for arm in ("r0", "r1") for k in (1, 2, 3))
    random.Random(20261013).shuffle(expected)
    assert queue == expected and len(set(queue)) == 18
    assert r.slot_queue(list(reversed(records))) == queue


def test_canary_takes_the_first_two_r0_and_r1_slots_in_queue_order(world):
    queue = r.slot_queue(world["manifest"]["records"])
    canary = r.canary_slots(queue)
    assert [slot[1] for slot in canary].count("r0") == 2 and [slot[1] for slot in canary].count("r1") == 2
    assert canary == [slot for i, slot in enumerate(queue) if [s[1] for s in queue[: i + 1]].count(slot[1]) <= 2]


def test_mock_slots_take_two_per_arm_from_different_repos():
    records = [{"task": task, "first": "b0r1", "sha256": "x"} for task in ("a__a-1", "b__b-1", "c__c-1", "d__d-1", "e__e-1")]
    repo_of = {row["task"]: row["task"].split("__")[0] for row in records}
    chosen = r.mock_slots(r.slot_queue(records), repo_of)
    assert sorted(slot[1] for slot in chosen) == ["r0", "r0", "r1", "r1"]
    assert len({repo_of[slot[0]] for slot in chosen}) == 4


def test_expected_prompts_pin_r0_to_a5_and_r1_to_the_record(world):
    expected = r.expected_prompts(world["manifest"], world["prepared"], world["tmp"])
    r0, r1 = expected[("pkg__pkg-1", "b0r3", "r0")], expected[("pkg__pkg-1", "b0r3", "r1")]
    record = (world["tmp"] / "attempts" / "pkg__pkg-1__b0r3.txt").read_text(encoding="utf-8")
    assert r0["text"] == _base("pkg__pkg-1") and r0["suffix"] is None and r0["sha256"] == world["manifest"]["records"][0]["a5_prompt_sha256"]
    assert r1["text"] == _base("pkg__pkg-1") + "\n\n" + record and r1["suffix"] == record
    assert r0["retry"] == {"arm": "r0", "first": "b0r3", "attempt_sha256": None}
    assert r1["retry"] == {"arm": "r1", "first": "b0r3", "attempt_sha256": _sha(record)}


def test_expected_prompts_refuse_a_changed_a5_prompt_or_record(world):
    world["manifest"]["records"][0]["a5_prompt_sha256"] = "0" * 64
    with pytest.raises(SystemExit, match="R0 prompt for pkg__pkg-1 differs"):
        r.expected_prompts(world["manifest"], world["prepared"], world["tmp"])
    world["manifest"]["records"][0]["a5_prompt_sha256"] = _sha(_base("pkg__pkg-1"))
    (world["tmp"] / "attempts" / "lib__lib-2__b0r2.txt").write_text("edited", encoding="utf-8")
    with pytest.raises(SystemExit, match="does not match the manifest sha256"):
        r.expected_prompts(world["manifest"], world["prepared"], world["tmp"])


def test_all_slots_run_with_their_suffix_and_retry_and_pass_the_injection_check(world, monkeypatch):
    calls = _fake_runner(monkeypatch, artifact=True)
    report = _run(world)
    assert report["halt_reason"] is None and report["started"] == 18 and report["injection_verified_runs"] == 18
    assert report["started_by_arm"] == {"r0": 9, "r1": 9}
    order = [(c["output"].parent.parent.parent.name, c["output"].parent.parent.name, c["output"].parent.name, int(c["output"].name[1:])) for c in calls]
    assert order == r.slot_queue(world["manifest"]["records"])
    for call in calls:
        arm = call["output"].parent.parent.name
        assert call["variant"] == "B0" and call["mock"] is False
        assert (call["suffix"] is None) == (arm == "r0") and call["retry"]["arm"] == arm
    assert json.loads((world["out"] / "test-report.json").read_text(encoding="utf-8"))["attempts_sha256"] == "a" * 64
    assert _run(world)["started"] == 0


def test_a_wrong_first_user_message_halts(world, monkeypatch):
    _fake_runner(monkeypatch, tamper=lambda prompt, retry: prompt + " " if retry["arm"] == "r1" else prompt)
    report = _run(world)
    assert report["halt_reason"].startswith("injection check failed") and "prompt_sha256 differs" in report["halt_reason"]
    assert report["started"] == next(i for i, slot in enumerate(r.slot_queue(world["manifest"]["records"])) if slot[1] == "r1") + 1


def test_a_first_user_message_that_differs_from_the_recorded_sha_halts(world, monkeypatch):
    calls = _fake_runner(monkeypatch)
    _run(world, [("pkg__pkg-1", "r1", "b0r1", 1)])
    run_dir = calls[0]["output"]
    _events(run_dir, "something else")
    expected = r.expected_prompts(world["manifest"], world["prepared"], world["tmp"])
    assert "first user message differs" in r.halt_reason(world["out"], expected)


def test_r0_prompt_that_differs_from_a5_halts(world, monkeypatch):
    _fake_runner(monkeypatch, tamper=lambda prompt, retry: prompt + "!" if retry["arm"] == "r0" else prompt)
    report = _run(world)
    assert "prompt_sha256 differs" in report["halt_reason"] and "/r0/" in report["halt_reason"]


def test_record_changed_after_start_stops_before_the_run(world, monkeypatch):
    calls = _fake_runner(monkeypatch)
    manifest = world["manifest"]
    expected = r.expected_prompts(manifest, world["prepared"], world["tmp"])
    (world["tmp"] / "attempts" / "pkg__pkg-1__b0r1.txt").write_text("edited", encoding="utf-8")
    report = asyncio.run(r.run_slots([("pkg__pkg-1", "r1", "b0r1", 1)], mock=False, out_root=world["out"], manifest=manifest,
                                     expected=expected, prepared=world["prepared"], attempts_sha256="a" * 64, label="t",
                                     record_root=world["tmp"]))
    assert calls == [] and "does not match the manifest sha256" in report["halt_reason"]


def test_infra_error_is_retired_and_rerun_at_most_twice(world, monkeypatch):
    monkeypatch.setattr(run_a5_main, "INFRA_STOP_RATIO", Decimal("1"))
    calls = _fake_runner(monkeypatch, statuses=["infra_error"] * 3)
    report = _run(world, [("pkg__pkg-1", "r0", "b0r1", 2)])
    slot = world["out"] / "pkg__pkg-1" / "r0" / "b0r1"
    assert len(calls) == 3 and sorted(p.name for p in slot.iterdir()) == ["r2", "r2.infra1", "r2.infra2"]
    assert len(report["infra_retired"]) == 2
    assert len(report["infra_kept"]) == 1 and report["infra_kept"][0].endswith("pkg__pkg-1/r0/b0r1/r2")


def test_infra_errors_above_ten_percent_halt(world, monkeypatch):
    monkeypatch.setattr(run_a5_main, "MAX_INFRA_RERUNS", 0)
    _fake_runner(monkeypatch, statuses=["infra_error"] * 18)
    report = _run(world)
    assert report["halt_reason"] == "infra_error 3 of 3 completed runs" and report["started"] == 3


def test_spend_cap_halts(world, monkeypatch):
    _fake_runner(monkeypatch, cost="100")
    report = _run(world)
    assert report["halt_reason"] == "spend 300 CNY reached the cap 210" and report["started"] == 3


def test_model_identity_change_halts(world, monkeypatch):
    calls = _fake_runner(monkeypatch)
    _run(world, [("pkg__pkg-1", "r0", "b0r1", 1)])
    _fake_runner(monkeypatch, model={"name": "deepseek-flash", "base_url_host": "other.example.com"})
    report = _run(world, [("pkg__pkg-1", "r0", "b0r1", 2), ("pkg__pkg-1", "r0", "b0r1", 3)])
    assert calls and "base_url host differs" in report["halt_reason"] and report["started"] == 1


def test_isolation_failure_and_harness_tool_errors_halt(world, monkeypatch):
    calls = _fake_runner(monkeypatch)
    _run(world, [("pkg__pkg-1", "r0", "b0r1", 1)])
    expected = r.expected_prompts(world["manifest"], world["prepared"], world["tmp"])
    path = calls[0]["output"] / "summary.json"
    row = json.loads(path.read_text(encoding="utf-8"))
    path.write_text(json.dumps(dict(row, answer_isolation_pass=False)), encoding="utf-8")
    assert r.halt_reason(world["out"], expected).startswith("answer isolation failed")
    path.write_text(json.dumps(dict(row, harness_tool_errors=1)), encoding="utf-8")
    assert r.halt_reason(world["out"], expected).startswith("harness tool errors")


def test_existing_summaries_must_belong_to_the_slot(world, monkeypatch):
    _fake_runner(monkeypatch)
    _run(world, [("pkg__pkg-1", "r1", "b0r1", 1)], mock=True)
    with pytest.raises(SystemExit, match="summary is a mock run"):
        _run(world, [("pkg__pkg-1", "r1", "b0r1", 1)])
    path = world["out"] / "pkg__pkg-1" / "r1" / "b0r1" / "r1" / "summary.json"
    row = json.loads(path.read_text(encoding="utf-8"))
    path.write_text(json.dumps(dict(row, mock=False, retry=dict(row["retry"], first="b0r3"))), encoding="utf-8")
    with pytest.raises(SystemExit, match="retry is"):
        _run(world, [("pkg__pkg-1", "r1", "b0r1", 1)])
    (world["out"] / "pkg__pkg-1" / "r0" / "b0r1" / "r1").mkdir(parents=True)
    with pytest.raises(SystemExit, match="interrupted run"):
        _run(world, [("pkg__pkg-1", "r0", "b0r1", 1)])


def test_runs_file_has_the_prereg_fields(world, monkeypatch):
    _fake_runner(monkeypatch)
    _run(world)
    path = r.write_runs(manifest=world["manifest"], attempts_sha256="a" * 64, repo_of=world["repo_of"], mock=False,
                        out_root=world["out"], destination=world["tmp"] / "a6-retry-runs.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert (payload["schema"], payload["scope"], payload["attempts_sha256"]) == ("a6.retry-runs.v1", "a6-retry", "a" * 64)
    assert len(payload["runs"]) == payload["slots_expected"] == 18
    for row in payload["runs"]:
        assert set(row) == PREREG_FIELDS and row["mock"] is False and isinstance(row["k"], int)
        assert row["run_dir"].endswith("/".join([row["task_id"], row["arm"], row["first"], "r" + str(row["k"])]))
        assert row["retry"]["arm"] == row["arm"] and row["retry"]["first"] == row["first"]
        assert (row["retry"]["attempt_sha256"] is None) == (row["arm"] == "r0")
    assert {row["repo"] for row in payload["runs"]} == {"pkg/pkg", "lib/lib"}


def test_mock_runs_file_is_scoped_mock_and_refuses_real_summaries(world, monkeypatch):
    _fake_runner(monkeypatch)
    _run(world, [("lib__lib-2", "r0", "b0r2", 1)], mock=True)
    path = r.write_runs(manifest=world["manifest"], attempts_sha256="a" * 64, repo_of=world["repo_of"], mock=True,
                        out_root=world["out"], destination=world["tmp"] / "mock.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["scope"] == "mock" and [row["mock"] for row in payload["runs"]] == [True]
    with pytest.raises(SystemExit, match="summary is a mock run"):
        r.write_runs(manifest=world["manifest"], attempts_sha256="a" * 64, repo_of=world["repo_of"], mock=False,
                     out_root=world["out"], destination=world["tmp"] / "real.json")


def test_load_attempts_refuses_a_manifest_from_another_template(world, tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(world["manifest"]), encoding="utf-8")
    manifest, sha = r.load_attempts(path, expected=(3, 2))
    assert len(manifest["records"]) == 3 and len(sha) == 64
    with pytest.raises(SystemExit, match="recount"):
        r.load_attempts(path)
    path.write_text(json.dumps(dict(world["manifest"], template_sha256="0" * 64)), encoding="utf-8")
    with pytest.raises(SystemExit, match="template_sha256"):
        r.load_attempts(path, expected=(3, 2))


def test_parse_slot():
    assert r.parse_slot("pkg__pkg-1/r1/b0r2/r3") == ("pkg__pkg-1", "r1", "b0r2", 3)
    with pytest.raises(SystemExit):
        r.parse_slot("pkg__pkg-1/r2/b0r2/r3")


def test_mock_slots_flag_requires_mock(monkeypatch):
    monkeypatch.setattr("sys.argv", ["run_a6_retry.py", "--mock-slots"])
    with pytest.raises(SystemExit, match="only allowed with --mock"):
        r.main()


@pytest.mark.skipif(not r.ATTEMPTS.is_file(), reason="needs docs/sprint/a6-attempts.json")
def test_the_committed_records_give_318_slots_and_a_fixed_canary():
    manifest, _ = r.load_attempts()
    queue = r.slot_queue(manifest["records"])
    assert len(queue) == len(set(queue)) == r.EXPECTED_SLOTS == 318
    canary = r.canary_slots(queue)
    assert [slot[1] for slot in canary].count("r0") == 2 and [slot[1] for slot in canary].count("r1") == 2
    for arm in ("r0", "r1"):
        assert [slot for slot in canary if slot[1] == arm] == [slot for slot in queue if slot[1] == arm][:2]
