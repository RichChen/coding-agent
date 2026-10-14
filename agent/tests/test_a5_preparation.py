import json
from collections import Counter

import pytest

from reposkill_agent.experiments.contracts import ExperimentContract
from reposkill_agent.experiments.preparation import (
    PUBLIC_COLUMNS,
    REPOSITORIES,
    SourceLock,
    assignments,
    make_public_task,
    prepare_pilot20,
    public_issue,
    readiness,
    select_issues,
)
from reposkill_agent.protocol.public import decode_public_task, digest


def raw_rows():
    rows = []
    for repo in REPOSITORIES:
        for n in range(6):
            rows.append(
                {
                    "repo": repo,
                    "instance_id": repo.replace("/", "__") + f"-{n}",
                    "base_commit": digest(repo + str(n))[:40],
                    "created_at": f"{2018 if n == 0 else 2021}-01-0{n + 1}T00:00:00Z",
                    "problem_statement": f"Investigate {repo} public example {n}.",
                    "patch": "PRIVATE_PATCH_SENTINEL",
                    "test_patch": "PRIVATE_TEST_SENTINEL",
                    "hints_text": "PRIVATE_HINT_SENTINEL",
                    "FAIL_TO_PASS": '["private_test"]',
                    "PASS_TO_PASS": '["private_regression"]',
                    "version": "private-version",
                    "environment_setup_commit": "a" * 40,
                }
            )
    return rows


def contract():
    return ExperimentContract(
        experiment_id="pilot20-test",
        mode="pilot_template",
        target_count=20,
        repeats=3,
        seeds=(42, 43, 44),
    )


def test_selection_is_order_independent_and_blind_to_private_answers():
    rows = raw_rows()
    first = select_issues(tuple(public_issue(r) for r in rows))
    changed = [
        {
            **r,
            "patch": "different",
            "FAIL_TO_PASS": "invalid-private-json",
            "hints_text": "answer-changed",
        }
        for r in reversed(rows)
    ]
    assert select_issues(tuple(public_issue(r) for r in changed)) == first
    targets, history, ledger = first
    assert Counter(i.repo for i in targets) == {repo: 4 for repo in REPOSITORIES}
    assert len(history) == 5 and len(ledger) == len(rows)
    assert not {i.instance_id for i in targets} & {i.instance_id for i in history}
    assert max(i.created_at for i in history) < min(i.created_at for i in targets)


def test_insufficient_sources_never_backfill_with_wrong_repo_or_old_task():
    rows = [r for r in raw_rows() if r["repo"] != REPOSITORIES[0]]
    with pytest.raises(ValueError, match="insufficient_public_candidates"):
        select_issues(tuple(public_issue(r) for r in rows))


def test_duplicate_instances_bases_and_issue_text_refused():
    rows = raw_rows()
    with pytest.raises(ValueError, match="duplicate_source_instance"):
        select_issues(tuple(public_issue(r) for r in rows + rows[:1]))
    for key, value, expected in (
        ("base_commit", "b" * 40, "duplicate_selected_base"),
        ("problem_statement", "same public issue", "duplicate_selected_issue"),
    ):
        changed = [{**r, key: value} for r in rows]
        with pytest.raises(ValueError, match=expected):
            select_issues(tuple(public_issue(r) for r in changed))


def test_240_assignments_balanced_and_exactly_once_with_common_profile():
    targets, _, _ = select_issues(tuple(public_issue(r) for r in raw_rows()))
    tasks = tuple(make_public_task(i) for i in targets)
    planned = assignments(tasks, contract())
    assert assignments(tuple(reversed(tasks)), contract()) == planned
    assert len(planned) == len({a["assignment_id"] for a in planned}) == 240
    assert len({(a["task_id"], a["variant"], a["repeat_id"]) for a in planned}) == 240
    assert Counter((a["variant"], a["pair_position"]) for a in planned) == {
        (v, n): 15 for v in contract().variants for n in range(4)
    }
    assert all(a["state"] == "planned_not_started" and a["provider_seed"] is None for a in planned)
    assert len({a["profile_hash"] for a in planned}) == 1
    for key, value in (("execution_profile_ref", "unsafe-host"), ("allowed_tools", ("read",))):
        bad = (tasks[0].model_copy(update={key: value}), *tasks[1:])
        with pytest.raises(ValueError, match="assignment_runtime_profile"):
            assignments(bad, contract())


def test_opaque_public_task_projection_and_permanent_preparation_stop():
    issue = public_issue(raw_rows()[0])
    task = make_public_task(issue)
    decoded, _ = decode_public_task(task.model_dump(mode="json"))
    assert decoded.issue_text == issue.problem_statement
    assert "PRIVATE_" not in task.model_dump_json()
    assert issue.instance_id not in task.task_id
    ready = readiness(selected=20, missing_history=[])
    assert not ready["real_api_enabled"] and not ready["pilot_started"]
    assert "explicit_user_A5_budget_approval" in ready["blockers"]
    assert ready["qualified_runnable_tasks"] == 0


def write_source(tmp_path):
    pa = pytest.importorskip("pyarrow")
    pq = pytest.importorskip("pyarrow.parquet")
    source = tmp_path / "source.parquet"
    pq.write_table(pa.Table.from_pylist(raw_rows()), source)
    lock = SourceLock(
        dataset="test-only",
        revision="a" * 40,
        split="test",
        source_url="https://example.invalid/resolve/" + "a" * 40 + "/test.parquet",
        sha256=digest(source.read_bytes()),
        size_bytes=source.stat().st_size,
        rows=30,
        readme_sha256="b" * 64,
        retrieved_on="2026-09-21",
        license_status="test-only",
        created_at_semantics="fixture PR creation",
    )
    lock_path = tmp_path / "lock.json"
    lock_path.write_text(lock.model_dump_json(), encoding="utf-8")
    return source, lock_path


def test_bundle_public_private_separation_hashes_and_no_budget_inheritance(tmp_path):
    source, lock = write_source(tmp_path)
    output = tmp_path / "bundle"
    report = prepare_pilot20(source, lock, output)
    assert report["target_candidates"] == 20 and report["planned_task_runs"] == 240
    assert report["started_runs"] == report["external_model_calls"] == 0
    assert report["repair_success"] is None
    public_files = list((output / "public").rglob("*.json"))
    assert len(public_files) == 21
    for file in public_files:
        text = file.read_text(encoding="utf-8")
        assert not any(
            s in text for s in ("PRIVATE_", "private_test", "FAIL_TO_PASS", "gold.patch")
        )
    manifest = json.loads((output / "artifact-manifest.json").read_text())
    assert all(digest((output / path).read_bytes()) == sha for path, sha in manifest.items())
    request = json.loads((output / "budget-request.DRAFT.json").read_text())
    assert request["approved_amount"] is None and not request["other_thread_budget_inherited"]
    assert request["verified_current_price"] is None and not request["reserve_allows_extra_runs"]
    with pytest.raises(FileExistsError):
        prepare_pilot20(source, lock, output)


def test_source_tampering_stops_before_any_output(tmp_path):
    source, lock = write_source(tmp_path)
    source.write_bytes(source.read_bytes() + b"tamper")
    with pytest.raises(ValueError, match="source_lock_mismatch"):
        prepare_pilot20(source, lock, tmp_path / "output")
    assert not (tmp_path / "output").exists()


def test_private_column_mutation_cannot_change_public_tasks_or_assignments(tmp_path):
    pa = pytest.importorskip("pyarrow")
    pq = pytest.importorskip("pyarrow.parquet")
    source, lock = write_source(tmp_path)
    prepare_pilot20(source, lock, tmp_path / "before")
    rows = raw_rows()
    for row in rows:
        for key in row.keys() - set(PUBLIC_COLUMNS):
            row[key] = (
                '["OTHER_PRIVATE_VALUE"]'
                if key in ("FAIL_TO_PASS", "PASS_TO_PASS")
                else "OTHER_PRIVATE_VALUE"
            )
    pq.write_table(pa.Table.from_pylist(rows), source)
    meta = json.loads(lock.read_text())
    meta.update(sha256=digest(source.read_bytes()), size_bytes=source.stat().st_size)
    lock.write_text(json.dumps(meta))
    prepare_pilot20(source, lock, tmp_path / "after")
    for before in (tmp_path / "before/public").rglob("*.json"):
        after = tmp_path / "after/public" / before.relative_to(tmp_path / "before/public")
        assert before.read_bytes() == after.read_bytes()
    assert (tmp_path / "before/assignments.json").read_bytes() == (
        tmp_path / "after/assignments.json"
    ).read_bytes()
