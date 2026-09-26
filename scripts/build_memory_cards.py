"""Build memory cards from any sprint5 handoff. Source ids are not hard-coded."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from reposkill_agent.memory.cards import render_card
from reposkill_agent.memory.cards_v5 import (
    HandoffFieldMissing,
    PilotTargetInSources,
    build_cards_from_handoff,
    cards_jsonl,
    load_handoff_document,
    manifest_for,
    published_sha256,
)

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "configs" / "a5" / "canonical-handoff.json"
PRIVATE = ROOT / "benchmarks" / "a5" / "pilot20-source-v1" / "private" / "test.parquet"
TARGETS = ROOT / "configs" / "a5" / "pilot20-harness-consumption-manifest.json"


def assert_no_private_answers(cards) -> None:
    blob = "\n".join(render_card(card) + "\n" + card.fix_approach + "\n" + "\n".join(card.test_commands) for card in cards)
    targets = json.loads(TARGETS.read_text(encoding="utf-8"))["targets"]
    for target in targets:
        if target in blob:
            raise ValueError("target_id_in_card:" + target)
    if not PRIVATE.is_file():
        return
    import pyarrow.parquet as pq

    table = pq.read_table(PRIVATE, columns=["instance_id", "patch", "test_patch", "FAIL_TO_PASS"])
    rows = {row["instance_id"]: row for row in table.to_pylist()}
    for target in targets:
        row = rows[target]
        for column in ("patch", "test_patch"):
            for line in str(row[column]).splitlines():
                if line.startswith("+") and not line.startswith("+++"):
                    snippet = line[1:].strip()
                    if len(snippet) >= 80 and snippet in blob:
                        raise ValueError("gold_or_test_patch_in_card:" + target)
        for node in str(row["FAIL_TO_PASS"]).replace(",", " ").split():
            if "::" in node and len(node) >= 40 and node in blob:
                raise ValueError("hidden_nodeid_in_card:" + target)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--handoff", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    try:
        cards, status = build_cards_from_handoff(
            args.handoff, canonical_path=CANONICAL, path_base=ROOT
        )
        assert_no_private_answers(cards)
    except (HandoffFieldMissing, PilotTargetInSources, ValueError) as exc:
        print("STOP", exc)
        return 2
    payload = cards_jsonl(cards)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(payload)
    if args.manifest:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        document = load_handoff_document(args.handoff)
        manifest = manifest_for(
            cards,
            payload,
            status=status,
            commit=commit,
            handoff_sha=published_sha256(args.handoff),
            handoff_schema=document["schema"],
        )
        args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"status={status} cards={len(cards)} bytes={len(payload)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
