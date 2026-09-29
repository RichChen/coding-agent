"""D6: predict which memory cards B2 injects for each pool task, without calling a model.

Runs the same steps as run_swe_task.run_task for variant B2: dated cards, the temporal filter, then
MemoryCardPlugin.decide on the public issue. Also counts, for description only, how many added lines of the
target's gold patch appear in the injected card text.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.run_a5_main import accepted_tasks, check_cards_manifest, load_targets, materialize_runner_task  # noqa: E402
from scripts.run_swe_task import dated_cards, handoff_dates, issue_text, load_json, target_created_at, temporal_filter  # noqa: E402
from src.runtime.window import view_hash  # noqa: E402

OUT = ROOT / "docs" / "sprint" / "b2-predicted-injection.json"
MIN_TASKS_WITH_CARDS = 10
NONTRIVIAL_CHARS = 10


def gold_added_lines(task: dict) -> list[str]:
    patch = json.loads((ROOT / task["private"]).read_text(encoding="utf-8"))["patch"]
    return [
        line[1:].strip() for line in patch.splitlines()
        if line.startswith("+") and not line.startswith("+++") and line[1:].strip()
    ]


def gold_overlap(task: dict, texts: list[str]) -> dict:
    card_lines = {line.strip() for text in texts for line in text.splitlines() if line.strip()}
    added = gold_added_lines(task)
    nontrivial = [line for line in added if len(line) >= NONTRIVIAL_CHARS]
    return {
        "gold_added_lines": len(added),
        "in_injected_text": sum(1 for line in added if line in card_lines),
        "gold_added_lines_nontrivial": len(nontrivial),
        "in_injected_text_nontrivial": sum(1 for line in nontrivial if line in card_lines),
    }


async def predict_one(task: dict, cards_path: Path, plugin_cls, load_cards) -> dict:
    prepared = materialize_runner_task(task)
    loaded = load_cards(cards_path)
    dates = handoff_dates()
    created_at = target_created_at(prepared["id"], dates)
    cards, _ = temporal_filter(loaded, task_id=prepared["id"], repo=prepared["repo"], created_at=created_at, dates=dates)
    public = load_json(Path(prepared["public_task"]))
    plugin = plugin_cls(variant="B2", cards=cards, repo=prepared["repo"], issue=issue_text(public), target_root=ROOT / prepared["original"])
    decision = await plugin.decide({})
    events = decision.get("events") or []
    items = [item for event in events for item in event.get("items") or []]
    candidates = decision.get("candidates") or []
    injected = [
        {"id": c["id"], "bytes": len(c["text"].encode()), "sha256": view_hash(c["text"])}
        for c in candidates
    ]
    selected = [item["source_id"] for item in items if item.get("status") == "selected"]
    if selected != [row["id"] for row in injected]:
        raise SystemExit("plugin events and candidates disagree for " + prepared["id"])
    kept = [card.source_id for card in cards]
    return {
        "id": prepared["id"],
        "repo": prepared["repo"],
        "created_at": created_at,
        "cards_after_filter": kept,
        "decision": events[0].get("status") if events else None,
        "injected": injected,
        "injected_bytes": sum(row["bytes"] for row in injected),
        "not_injected": [
            {"id": item["source_id"], "status": item.get("status"), "bytes": item.get("bytes")}
            for item in items if item.get("status") != "selected"
        ],
        "gold_overlap": gold_overlap(task, [c["text"] for c in candidates]),
    }


def audit(rows: list[dict], cards_by_id: dict) -> dict:
    """Every injected card is same-repo, older than the target, and not the target itself."""
    from scripts.run_swe_task import parse_created_at

    later, own, cross = [], [], []
    for row in rows:
        target = parse_created_at(row["created_at"], row["id"])
        for item in row["injected"]:
            card = cards_by_id[item["id"]]
            if item["id"] == row["id"]:
                own.append(row["id"])
            if card["repo"] != row["repo"]:
                cross.append(row["id"] + " <- " + item["id"])
            if parse_created_at(card["created_at"], item["id"]) >= target:
                later.append(row["id"] + " <- " + item["id"])
    return {"later_than_target": later, "own_task": own, "cross_repo": cross}


async def predict(cards_path: Path) -> dict:
    checked = check_cards_manifest(cards_path)
    from src.policy.reposkill import load_adapter, source_digest

    agent_root = ROOT.parent / "coding-agent"
    load_adapter(agent_root, source_digest(agent_root))
    from reposkill_agent.memory.card_plugin import MemoryCardPlugin
    from reposkill_agent.memory.cards import load_memory_cards

    dated = dated_cards(cards_path)
    tasks = accepted_tasks(load_targets())
    rows = [await predict_one(task, dated, MemoryCardPlugin, load_memory_cards) for task in tasks]
    cards_by_id = {}
    for line in dated.read_text(encoding="utf-8").splitlines():
        if line.strip():
            card = json.loads(line)
            cards_by_id[card["source_id"]] = card
    with_cards = [row for row in rows if row["injected"]]
    sizes = [row["injected_bytes"] for row in with_cards]
    overlap = [row["gold_overlap"] for row in with_cards]
    return {
        "schema": "sprint6.b2-predicted-injection.v1",
        "variant": "B2",
        "cards": checked["cards"],
        "cards_sha256": checked["cards_sha256"],
        "handoffs": checked["handoffs"],
        "tasks": len(rows),
        "tasks_with_cards": len(with_cards),
        "cards_injected_total": sum(len(row["injected"]) for row in rows),
        "mean_injected_bytes_when_injected": round(statistics.mean(sizes), 1) if sizes else 0,
        "gold_overlap_summary": {
            "tasks_with_any_overlap": sum(1 for row in overlap if row["in_injected_text"]),
            "tasks_with_nontrivial_overlap": sum(1 for row in overlap if row["in_injected_text_nontrivial"]),
            "lines_in_injected_text": sum(row["in_injected_text"] for row in overlap),
            "nontrivial_lines_in_injected_text": sum(row["in_injected_text_nontrivial"] for row in overlap),
            "nontrivial_min_chars": NONTRIVIAL_CHARS,
        },
        "audit": audit(rows, cards_by_id),
        "runs": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cards", required=True)
    parser.add_argument("--out", default=str(OUT))
    args = parser.parse_args()
    cards = Path(args.cards)
    if not cards.is_absolute():
        cards = ROOT / cards
    table = asyncio.run(predict(cards))
    out = Path(args.out)
    out.write_text(json.dumps(table, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    bad = {key: value for key, value in table["audit"].items() if value}
    print(json.dumps({key: table[key] for key in ("tasks", "tasks_with_cards", "cards_injected_total",
                                                  "mean_injected_bytes_when_injected", "gold_overlap_summary", "audit")}, indent=2))
    if bad:
        raise SystemExit("an injected card is later, the target itself, or from another repo: " + json.dumps(bad))
    if table["tasks_with_cards"] < MIN_TASKS_WITH_CARDS:
        raise SystemExit("only " + str(table["tasks_with_cards"]) + " tasks get a card; stop for audit")


if __name__ == "__main__":
    main()
