"""Rebuild memory cards from event logs. Rule extraction only; v2 is left in place."""

from __future__ import annotations

import json
import re
from pathlib import Path

from reposkill_agent.memory.cards import render_card, write_memory_cards
from reposkill_agent.memory.event_extract import SourceExtraction, _keep_command, extract_source
from reposkill_agent.memory.legacy_env import is_legacy_env_artifact
from reposkill_agent.memory.records import CardDependency, MemoryCard
from reposkill_agent.memory.source_verification import load_source_verification

NONE_RUN = "none run in source attempt"
_FACT = re.compile(r"runtests\.py|testing/|must .{0,40}together|changed together", re.IGNORECASE)


def build_memory_cards_v3(snapshot_path: Path, verification_path: Path) -> tuple[MemoryCard, ...]:
    rows = [json.loads(line) for line in snapshot_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    labels = load_source_verification(verification_path, tuple(row["source_id"] for row in rows))
    return tuple(_card(row, labels[row["source_id"]]) for row in rows)


def _card(row: dict, status: str) -> MemoryCard:
    source = Path(row["source_dir"])
    trajectory = json.loads((source / "public-trajectory.json").read_text(encoding="utf-8"))
    extracted = extract_source(source, row["source_id"])
    commands = _test_commands(extracted.commands)
    files = _files(extracted)
    symbols = extracted.changed_symbols
    return MemoryCard(
        repo=row["bindings"]["repo"],
        version=row["bindings"]["base_revision"],
        source_id=row["source_id"],
        issue_summary=_compact(str(trajectory.get("issue_summary") or "issue")),
        relevant_files=files,
        test_commands=commands[:4] or (NONE_RUN,),
        env_pitfalls=_pitfalls(extracted, commands),
        fix_approach=_approach(extracted, symbols),
        verification_status=status,  # type: ignore[arg-type]
        dependencies=_dependencies(extracted),
        distillation="rule",
        observations=tuple(str(item) for item in trajectory.get("public_evidence") or ()),
        actions=tuple(str(item) for item in trajectory.get("actions") or ()),
        public_verification=str(trajectory.get("public_verification") or ""),
        failure_notes=tuple(str(item) for item in trajectory.get("failure_notes") or ()),
    )


def _shell_parts(command: str) -> list[str]:
    parts, buf, quote = [], [], ""
    index = 0
    while index < len(command):
        char = command[index]
        if quote:
            buf.append(char)
            if char == quote:
                quote = ""
            index += 1
            continue
        if char in "\"'":
            quote = char
            buf.append(char)
            index += 1
            continue
        if command.startswith("&&", index) or char in {";", "|"}:
            parts.append("".join(buf).strip())
            buf = []
            index += 2 if command.startswith("&&", index) else 1
            continue
        buf.append(char)
        index += 1
    if buf:
        parts.append("".join(buf).strip())
    return [part for part in parts if part]


def _test_commands(commands: tuple[str, ...]) -> tuple[str, ...]:
    kept = []
    for command in commands:
        for part in _shell_parts(command):
            if _keep_command(part) and not is_legacy_env_artifact(part) and part not in kept:
                kept.append(part[:180])
    return tuple(kept[:4])


def _files(extracted: SourceExtraction) -> tuple[str, ...]:
    ranges = {}
    for span in extracted.reads:
        if span.start and span.end:
            ranges.setdefault(span.path, f"{span.start}-{span.end}")
    ordered = []
    for path in extracted.edited_paths:
        ordered.append(path + (":" + ranges[path] if path in ranges else ""))
    for span in extracted.reads:
        if span.path in extracted.edited_paths or span.path in {".", "./"}:
            continue
        label = span.path + (f":{span.start}-{span.end}" if span.start and span.end else "")
        if label not in ordered and span.path not in ordered:
            ordered.append(label)
    return tuple(ordered[:8])


def _approach(extracted: SourceExtraction, symbols: tuple[str, ...]) -> str:
    diagnosis = extracted.diagnosis or extracted.final_answer or "The source attempt did not state a cause."
    names = ", ".join(symbols[:6]) if symbols else "no named function or class"
    text = f"{_compact(diagnosis)} Changed {names}."
    return text[:700]


def _pitfalls(extracted: SourceExtraction, commands: tuple[str, ...]) -> tuple[str, ...]:
    found = []
    for text in (extracted.diagnosis, extracted.final_answer, *commands):
        if not text or is_legacy_env_artifact(text):
            continue
        if _FACT.search(text):
            line = _compact(text)[:180]
            if line not in found:
                found.append(line)
    if len(extracted.edited_paths) > 1:
        together = "Change together: " + ", ".join(extracted.edited_paths[:4])
        if together not in found:
            found.append(together)
    return tuple(found[:3])


def _dependencies(extracted: SourceExtraction) -> tuple[CardDependency, ...]:
    symbols = tuple(dict.fromkeys(name.split(".")[-1] for name in extracted.changed_symbols))[:6]
    deps = []
    for path in extracted.edited_paths:
        base = path.split(":")[0]
        deps.append(CardDependency(path=base, symbols=symbols if base.endswith(".py") else ()))
    return tuple(deps)


def _compact(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def rendered_cards(cards: tuple[MemoryCard, ...]) -> tuple[str, ...]:
    return tuple(render_card(card) for card in cards)


__all__ = ["NONE_RUN", "build_memory_cards_v3", "rendered_cards", "write_memory_cards"]
