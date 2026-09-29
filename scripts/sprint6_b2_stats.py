#!/usr/bin/env python3
"""CHECKPOINT-6 (D8) statistics for B2 and the b0/r4 drift slots under runs/a5-main/. No model calls.

Solve rates are left out on purpose: D8 does not compare B2 with B0. The fault-alarm inputs are the only
outcome fields reported.
"""
from __future__ import annotations

import json
import statistics
import sys
from collections import Counter
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_a5_main import FAULT_ALARM_RUNS, PREDICTED, accepted_tasks, load_targets, out_root_for  # noqa: E402
from scripts.run_swe_task import parse_created_at  # noqa: E402

CARDS = ROOT.parent / "coding-agent" / "benchmarks" / "a5" / "memory-cards-v6.jsonl"


def injected_records(run_dir: Path) -> list[dict]:
    """Memory-card items in context.prepared events, one entry per injection."""
    found = []
    events = run_dir / "events.jsonl"
    if not events.is_file():
        return found
    with events.open(encoding="utf-8") as handle:
        for line in handle:
            if '"context.prepared"' not in line:
                continue
            event = json.loads(line)
            if event.get("event_type") != "context.prepared":
                continue
            plugin = ((event.get("payload") or {}).get("stats") or {}).get("plugin") or {}
            found.extend(item for item in plugin.get("actually_injected") or [] if item.get("reason") == "memory_card")
    return found


def slot_rows(root: Path, pattern: str) -> tuple[list[dict], list[dict]]:
    formal, infra = [], []
    for path in sorted(root.glob(pattern)):
        row = json.loads(path.read_text(encoding="utf-8"))
        row["_slot"] = path.parent.name
        row["_dir"] = path.parent
        (infra if "." in row["_slot"] or row.get("status") == "infra_error" else formal).append(row)
    return formal, infra


def run_block(formal: list[dict], infra: list[dict], expected: int) -> dict:
    cost = sum((Decimal(str(row.get("cost_cny") or "0")) for row in formal + infra), Decimal("0"))
    return {
        "expected_slots": expected,
        "completed": len(formal),
        "stop_reason": dict(Counter(str(row.get("stop_reason")) for row in formal)),
        "infra": [{"task_id": row["task_id"], "slot": row["_slot"], "infra_reason": row.get("infra_reason")} for row in infra],
        "docker_retries": len([retry for row in formal + infra for retry in row.get("docker_retries") or []]),
        "harness_tool_errors": sum(row.get("harness_tool_errors") or 0 for row in formal + infra),
        "missing_runs": [row["task_id"] + "/" + row["_slot"] for row in formal if (row.get("grader_ids") or {}).get("missing")],
        "grader_candidate_error": [row["task_id"] + "/" + row["_slot"] for row in formal if row.get("grader_candidate_error")],
        "isolation_failed": [row["task_id"] + "/" + row["_slot"] for row in formal if row.get("answer_isolation_pass") is False],
        "models": sorted({json.dumps(row.get("model"), sort_keys=True) for row in formal}),
        "profiles": sorted({str(row.get("profile")) for row in formal}),
        "variants": sorted({str(row.get("variant")) for row in formal}),
        "cost_cny": str(cost),
        "mean_cost_cny": str((cost / len(formal + infra)).quantize(Decimal("0.001"))) if formal + infra else None,
        "mean_model_calls": round(statistics.mean(row.get("model_calls") or 0 for row in formal), 1) if formal else None,
    }


def main():
    root = out_root_for(False)
    tasks = {task["id"]: task for task in accepted_tasks(load_targets())}
    table = json.loads(PREDICTED.read_text(encoding="utf-8"))
    predicted = {row["id"]: row for row in table["runs"]}
    cards = {}
    for line in CARDS.read_text(encoding="utf-8").splitlines():
        if line.strip():
            card = json.loads(line)
            cards[card["source_id"]] = card

    b2, b2_infra = slot_rows(root, "*/b2/r*/summary.json")
    r4, r4_infra = slot_rows(root, "*/b0/r4*/summary.json")

    agree, disagree, detail_mismatch, preview_mismatch, missing_events, cards_on_later_steps = 0, [], [], [], [], []
    later, own, cross = [], [], []
    injected_bytes, injected_counts, injected_tasks = [], [], set()
    for row in b2:
        task_id = row["task_id"]
        records = injected_records(row["_dir"])
        if not (row["_dir"] / "events.jsonl").is_file():
            missing_events.append(task_id + "/" + row["_slot"])
            continue
        expected = predicted[task_id]["injected"]
        actual_ids = sorted({item["id"] for item in records})
        if actual_ids == sorted(item["id"] for item in expected):
            agree += 1
        else:
            disagree.append({"run": task_id + "/" + row["_slot"], "actual": actual_ids, "predicted": [item["id"] for item in expected]})
        by_id = {item["id"]: item for item in expected}
        for item in records:
            want = by_id.get(item["id"])
            if want and (item.get("bytes") != want["bytes"] or item.get("sha256") != want["sha256"]):
                detail_mismatch.append(task_id + "/" + row["_slot"] + " " + item["id"])
        if len(records) != len(actual_ids):
            cards_on_later_steps.append(task_id + "/" + row["_slot"])
        preview = [(item["id"], item["bytes"]) for item in (row.get("memory") or {}).get("injected") or []]
        if preview != [(item["id"], item["bytes"]) for item in expected]:
            preview_mismatch.append(task_id + "/" + row["_slot"])
        target = parse_created_at(tasks[task_id]["created_at"], task_id)
        for card_id in actual_ids:
            card = cards[card_id]
            if card_id == task_id:
                own.append(task_id + "/" + row["_slot"])
            if card["repo"] != tasks[task_id]["repo"]:
                cross.append(task_id + "/" + row["_slot"] + " <- " + card_id)
            if parse_created_at(card["created_at"], card_id) >= target:
                later.append(task_id + "/" + row["_slot"] + " <- " + card_id)
        if actual_ids:
            injected_tasks.add(task_id)
            injected_counts.append(len(actual_ids))
            injected_bytes.append(sum({item["id"]: item.get("bytes") or 0 for item in records}.values()))

    report = {
        "b2": run_block(b2, b2_infra, 3 * len(tasks)),
        "b0_r4": run_block(r4, r4_infra, len(tasks)),
        "b2_tasks_with_three_runs": sum(1 for task_id in tasks if sum(1 for row in b2 if row["task_id"] == task_id) == 3),
        "fault_alarm_inputs": {"b2_formal_runs": len(b2), "any_b2_solved": any(row.get("solved") for row in b2), "threshold": FAULT_ALARM_RUNS},
        "injection": {
            "predicted_table_cards_sha256": table["cards_sha256"],
            "runs_checked": len(b2) - len(missing_events),
            "runs_agree": agree,
            "runs_disagree": disagree,
            "bytes_or_sha_differs": detail_mismatch,
            "summary_preview_differs": preview_mismatch,
            "runs_without_events": missing_events,
            "runs_with_a_card_injected_more_than_once": cards_on_later_steps,
            "tasks_injected": len(injected_tasks),
            "runs_injected": len(injected_counts),
            "mean_cards_per_injected_run": round(statistics.mean(injected_counts), 2) if injected_counts else 0,
            "mean_bytes_per_injected_run": round(statistics.mean(injected_bytes), 1) if injected_bytes else 0,
        },
        "gold_overlap_predicted": table["gold_overlap_summary"],
        "audit": {"later_than_target": later, "own_task": own, "cross_repo": cross},
        "spent_total_cny": str(sum((Decimal(str(json.loads(p.read_text(encoding="utf-8")).get("cost_cny") or "0"))
                                    for p in root.rglob("summary.json")), Decimal("0"))),
    }
    destination = ROOT / "runs" / "a5-main-logs" / "b2-stats.json"
    destination.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
