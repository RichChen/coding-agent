"""Rule distillation of public source trajectories into memory cards.

No model calls. Gold patches, test patches, and target-task ids are never copied.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from reposkill_agent.memory.records import CardDependency, MemoryCard
from reposkill_agent.memory.source_verification import load_source_verification

EDIT_TOOLS = {"search_replace", "edit_file", "write_file"}
READ_TOOLS = {"read_file", "list_dir"}
RENDER_LIMIT = 1500
_SENTENCE = re.compile(r".+?[.!?。](?:\s|$)")
_COMMAND = re.compile(
    r"(?:^|[\n`])((?:python(?:\d+(?:\.\d+)?)? -m )?(?:pytest|tox|unittest)\b[^\n`]{0,160})",
    re.IGNORECASE,
)
_PITFALL = re.compile(
    r"(not found|ImportError|ModuleNotFoundError|No module named|PermissionError|"
    r"truncated=true|command not found|nonzero_exit)",
    re.IGNORECASE,
)
_IDENT = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]{2,}\b")
_DEF = re.compile(r"^(?:def|class)\s+([A-Za-z_][A-Za-z0-9_]*)", re.MULTILINE)

BANNER = (
    "[historical attempt on a different issue in this repo; status={status}"
    " — use as navigation hints, not as the answer]"
)


def build_memory_cards(snapshot_path: Path, verification_path: Path) -> tuple[MemoryCard, ...]:
    rows = []
    for line in snapshot_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    labels = load_source_verification(
        verification_path, tuple(row["source_id"] for row in rows)
    )
    return tuple(_card_from_row(row, labels[row["source_id"]]) for row in rows)


def write_memory_cards(cards: tuple[MemoryCard, ...], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps(card.model_dump(mode="json"), ensure_ascii=False, sort_keys=True) for card in cards
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_memory_cards(path: Path) -> tuple[MemoryCard, ...]:
    cards = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            cards.append(MemoryCard.model_validate(json.loads(line)))
    return tuple(cards)


def render_card(card: MemoryCard, *, limit: int = RENDER_LIMIT) -> str:
    header = BANNER.format(status=card.verification_status)
    files = ", ".join(card.relevant_files[:8]) or "(none)"
    tests = "; ".join(card.test_commands[:4]) or "(none)"
    pitfalls = "; ".join(card.env_pitfalls[:4]) or "(none)"
    deps = []
    for dep in card.dependencies[:6]:
        symbols = ",".join(dep.symbols[:4])
        deps.append(dep.path + (f"[{symbols}]" if symbols else ""))
    body = "\n".join(
        (
            header,
            f"repo: {card.repo} @ {card.version[:12]}",
            f"source: {card.source_id}",
            f"issue: {card.issue_summary}",
            f"files: {files}",
            f"tests: {tests}",
            f"pitfalls: {pitfalls}",
            f"approach: {card.fix_approach}",
            f"deps: {', '.join(deps) or '(none)'}",
        )
    )
    encoded = body.encode("utf-8")
    if len(encoded) <= limit:
        return body
    return encoded[: limit - 3].decode("utf-8", errors="ignore") + "..."


def raw_trajectory_text(card: MemoryCard) -> str:
    """B1 payload: truncated public trajectory, same shape as the old view."""
    return json.dumps(
        {
            "historical_issue": card.issue_summary[:500],
            "public_observations": [item[:240] for item in card.observations[:8]],
            "actions": list(card.actions[:20]),
            "public_verification": card.public_verification[:300],
            "failure_notes": list(card.failure_notes[:4]),
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _card_from_row(row: dict, status: str) -> MemoryCard:
    source = Path(row["source_dir"])
    trajectory = json.loads((source / "public-trajectory.json").read_text(encoding="utf-8"))
    delta_path = source / "candidate-delta.json"
    changed = {}
    if delta_path.is_file():
        delta = json.loads(delta_path.read_text(encoding="utf-8"))
        changed = delta.get("changed") or {}
    actions = tuple(str(item) for item in trajectory.get("actions") or ())
    observations = tuple(str(item) for item in trajectory.get("public_evidence") or ())
    notes = tuple(str(item) for item in trajectory.get("failure_notes") or ())
    issue = _summary(str(trajectory.get("issue_summary") or ""))
    files = _relevant_files(actions)
    dependencies = _dependencies(changed, issue)
    return MemoryCard(
        repo=row["bindings"]["repo"],
        version=row["bindings"]["base_revision"],
        source_id=row["source_id"],
        issue_summary=issue,
        relevant_files=files,
        test_commands=_commands(observations, notes),
        env_pitfalls=_pitfalls(observations, notes),
        fix_approach=_approach(issue, changed, files),
        verification_status=status,  # type: ignore[arg-type]
        dependencies=dependencies,
        distillation="rule",
        observations=observations,
        actions=actions,
        public_verification=str(trajectory.get("public_verification") or ""),
        failure_notes=notes,
    )


def _summary(text: str) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    sentences = _SENTENCE.findall(compact)
    chosen = "".join(sentences[:2]).strip() if sentences else compact
    return chosen[:500] if chosen else compact[:500]


def _split_action(action: str) -> tuple[str, str]:
    tool, _, path = action.partition(":")
    return tool, path.replace("\\", "/")


def _relevant_files(actions: tuple[str, ...]) -> tuple[str, ...]:
    edited, read = [], []
    for action in actions:
        tool, path = _split_action(action)
        if not path or path in {".", "./"}:
            continue
        if tool in EDIT_TOOLS and path not in edited:
            edited.append(path)
        elif tool in READ_TOOLS and path not in read and path not in edited:
            read.append(path)
    return tuple(edited + read)


def _commands(*groups: tuple[str, ...]) -> tuple[str, ...]:
    found = []
    for group in groups:
        for text in group:
            for match in _COMMAND.findall(text):
                command = re.sub(r"\s+", " ", match).strip()
                if command and command not in found:
                    found.append(command[:180])
    return tuple(found[:6])


def _pitfalls(observations: tuple[str, ...], notes: tuple[str, ...]) -> tuple[str, ...]:
    found = []
    for text in (*notes, *observations):
        if not _PITFALL.search(text):
            continue
        line = re.sub(r"\s+", " ", text).strip()[:180]
        if line and line not in found:
            found.append(line)
    return tuple(found[:4])


def _approach(issue: str, changed: dict, files: tuple[str, ...]) -> str:
    names = [name.replace("\\", "/") for name in changed if isinstance(name, str)]
    if not names:
        names = [path for path in files if path]
    shown = ", ".join(names[:6]) or "no files recorded"
    first = issue.split(". ")[0].strip()
    reads = [path for path in files if path not in names][:4]
    read_text = ", ".join(reads) if reads else "no extra files"
    return (
        f"The historical attempt edited {len(names)} path(s): {shown}. "
        f"The source issue starts: {first}. "
        f"Files inspected but not edited include: {read_text}. "
        "Use the paths as navigation hints for a different issue; the diff itself is not included."
    )


def _dependencies(changed: dict, issue: str) -> tuple[CardDependency, ...]:
    mentioned = set(_IDENT.findall(issue))
    deps = []
    for name, payload in changed.items():
        if not isinstance(name, str):
            continue
        path = name.replace("\\", "/")
        content = ""
        if isinstance(payload, dict):
            content = str(payload.get("content") or "")
        defined = set(_DEF.findall(content))
        symbols = tuple(sorted(defined & mentioned))[:4]
        if not symbols:
            symbols = tuple(sorted(mentioned & set(_IDENT.findall(content))))[:4]
        deps.append(CardDependency(path=path, symbols=symbols))
    return tuple(deps)
