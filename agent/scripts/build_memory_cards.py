"""Build memory cards from any sprint handoff. Source ids are not hard-coded."""

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
    build_cards_from_handoffs,
    cards_jsonl,
    manifest_for,
)

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "configs" / "a5" / "canonical-handoff.json"
PRIVATE = ROOT / "benchmarks" / "a5" / "pilot20-source-v1" / "private" / "test.parquet"
TARGETS = ROOT / "configs" / "a5" / "pilot20-harness-consumption-manifest.json"


def _parse_id_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str) and value.strip().startswith("["):
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    return []


def _hidden_nodes(card, harness_roots: list[Path]) -> list[str]:
    nodes: list[str] = []
    for root in harness_roots:
        private = root / "runs" / "sprint5-main-private" / f"{card.source_id}.json"
        if not private.is_file():
            continue
        data = json.loads(private.read_text(encoding="utf-8"))
        nodes.extend(_parse_id_list(data.get("FAIL_TO_PASS")))
        nodes.extend(_parse_id_list(data.get("PASS_TO_PASS")))
    run_text = card.source_run.split(" ", 1)[1]
    grader = Path(run_text) / "grader-result.json"
    if grader.is_file():
        data = json.loads(grader.read_text(encoding="utf-8"))
        for case in data.get("cases") or []:
            if isinstance(case, dict) and case.get("nodeid"):
                nodes.append(str(case["nodeid"]))
    return nodes


def scrub_hidden_ids(cards, harness_roots: list[Path]):
    """Remove source F2P/P2P ids from trajectory text. Leave the public issue unchanged."""
    from reposkill_agent.memory.cards_v3 import NONE_RUN

    cleaned = []
    for card in cards:
        nodes = [
            node
            for node in dict.fromkeys(_hidden_nodes(card, harness_roots))
            if "::" in node and len(node) >= 40
        ]
        if not nodes:
            cleaned.append(card)
            continue

        def hide(text: str) -> str:
            for node in nodes:
                text = text.replace(node, "[hidden-test]")
            return text

        commands = tuple(hide(command) for command in card.test_commands) or (NONE_RUN,)
        cleaned.append(
            card.model_copy(
                update={
                    "test_commands": commands,
                    "fix_approach": hide(card.fix_approach),
                    "observations": tuple(hide(item) for item in card.observations),
                    "actions": tuple(hide(item) for item in card.actions),
                    "failure_notes": tuple(hide(item) for item in card.failure_notes),
                    "env_pitfalls": tuple(hide(item) for item in card.env_pitfalls),
                }
            )
        )
    return tuple(cleaned)


def hidden_id_hit_counts(cards, harness_roots: list[Path]) -> tuple[int, int]:
    """Count source F2P/P2P ids in card text. Returns (outside issue, inside issue)."""
    outside = 0
    inside = 0
    for card in cards:
        issue = card.issue_summary
        other = "\n".join(
            [
                render_card(card).replace(issue, ""),
                card.fix_approach,
                "\n".join(card.test_commands),
                "\n".join(card.observations),
                "\n".join(card.actions),
            ]
        )
        for node in dict.fromkeys(_hidden_nodes(card, harness_roots)):
            if "::" not in node or len(node) < 40:
                continue
            if node in other:
                outside += 1
            elif node in issue:
                inside += 1
    return outside, inside


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
    parser.add_argument("--handoff", type=Path, action="append", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    try:
        cards, status, handoffs, omitted = build_cards_from_handoffs(
            args.handoff, canonical_path=CANONICAL, path_base=ROOT
        )
        assert_no_private_answers(cards)
        roots = []
        for path in args.handoff:
            root = path.resolve().parents[2]
            if root not in roots:
                roots.append(root)
        cards = scrub_hidden_ids(cards, roots)
        outside, inside = hidden_id_hit_counts(cards, roots)
    except (HandoffFieldMissing, PilotTargetInSources, ValueError) as exc:
        print("STOP", exc)
        return 2
    if outside:
        print(f"STOP f2p_p2p_id_hits={outside}")
        return 2
    payload = cards_jsonl(cards)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(payload)
    if args.manifest:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        manifest = manifest_for(
            cards,
            payload,
            status=status,
            commit=commit,
            handoff_sha=handoffs[0]["sha256"],
            handoff_schema=handoffs[0]["schema"],
            handoffs=handoffs,
            omitted_infra_only=list(omitted),
        )
        args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    rendered = sorted(len(render_card(card).encode("utf-8")) for card in cards)

    def percentile(fraction: float) -> int:
        if not rendered:
            return 0
        index = min(len(rendered) - 1, int(fraction * (len(rendered) - 1)))
        return rendered[index]

    print(
        f"status={status} cards={len(cards)} bytes={len(payload)} "
        f"f2p_p2p_id_hits={outside} issue_only_id_hits={inside} "
        f"rendered_bytes min={percentile(0)} p25={percentile(0.25)} "
        f"median={percentile(0.5)} p75={percentile(0.75)} max={percentile(1)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
