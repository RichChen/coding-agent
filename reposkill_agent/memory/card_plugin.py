"""BM25 retrieval over memory cards. The old public-episode plugin stays in place."""

from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path

from reposkill_agent.memory.cards import raw_trajectory_text, render_card
from reposkill_agent.memory.gate import validity_reasons
from reposkill_agent.memory.records import MemoryCard
from reposkill_agent.memory.validity import check_card_dependencies

STOPWORDS = frozenset(
    """
    a an the and or of to in on for with is are was were be been being this that it as at by
    from not no into over after before about than then so if but can will just than its their
    """.split()
)
_TOKEN = re.compile(r"[a-z][a-z0-9_]{2,}")
_PATH = re.compile(r"[A-Za-z0-9_./\\-]+\.[A-Za-z0-9]+")


def tokens(text: str) -> list[str]:
    return [item for item in _TOKEN.findall(text.lower()) if item not in STOPWORDS]


def retrieval_document(card: MemoryCard) -> str:
    deps = " ".join(
        dep.path + " " + " ".join(dep.symbols) for dep in card.dependencies
    )
    return " ".join(
        (
            card.issue_summary,
            " ".join(card.relevant_files),
            card.fix_approach,
            deps,
        )
    )


def bm25_scores(query: str, documents: list[str], *, k1: float = 1.2, b: float = 0.75) -> list[float]:
    q_terms = tokens(query)
    docs = [tokens(doc) for doc in documents]
    n_docs = len(docs)
    if not q_terms or not n_docs:
        return [0.0] * n_docs
    avg = sum(len(doc) for doc in docs) / n_docs or 1.0
    df: Counter[str] = Counter()
    for doc in docs:
        df.update(set(doc))
    scores = []
    for doc in docs:
        tf = Counter(doc)
        score = 0.0
        for term in q_terms:
            if term not in tf:
                continue
            idf = math.log(1 + (n_docs - df[term] + 0.5) / (df[term] + 0.5))
            freq = tf[term]
            score += idf * (freq * (k1 + 1)) / (freq + k1 * (1 - b + b * len(doc) / avg))
        scores.append(score)
    return scores


def path_bonus(issue: str, card: MemoryCard) -> float:
    mentioned = {item.replace("\\", "/").lower() for item in _PATH.findall(issue)}
    bonus = 0.0
    for path in card.relevant_files:
        name = path.replace("\\", "/").lower()
        if name in mentioned or Path(name).name in {Path(item).name for item in mentioned}:
            bonus += 2.0
    for dep in card.dependencies:
        for symbol in dep.symbols:
            if symbol.lower() in issue.lower():
                bonus += 1.0
    return bonus


def rank_cards(
    cards: tuple[MemoryCard, ...],
    *,
    repo: str,
    issue: str,
    min_score: float = 1.0,
) -> tuple[tuple[float, MemoryCard], ...]:
    pool = tuple(card for card in cards if card.repo == repo)
    documents = [retrieval_document(card) for card in pool]
    lexical = bm25_scores(issue, documents)
    ranked = []
    for card, base in zip(pool, lexical, strict=True):
        score = base + path_bonus(issue, card)
        if score >= min_score:
            ranked.append((score, card))
    ranked.sort(key=lambda item: (-item[0], item[1].source_id))
    return tuple(ranked)


class MemoryCardPlugin:
    """Data-only candidate policy. Host still owns execution and injection."""

    name = "reposkill-memory-card"
    schema_version = "0.1"

    def __init__(
        self,
        *,
        variant: str,
        cards: tuple[MemoryCard, ...],
        repo: str,
        issue: str,
        target_root: Path,
        max_bytes: int = 4096,
        min_score: float = 1.0,
    ):
        if variant not in {"B0", "B1", "B2", "B3"}:
            raise ValueError("invalid_variant")
        self.variant = variant
        self.cards = cards
        self.repo = repo
        self.issue = issue
        self.target_root = target_root
        self.max_bytes = max_bytes
        self.min_score = min_score

    async def decide(self, policy_input: dict) -> dict:
        previous = policy_input.get("state") or {}
        if previous.get("calls", 0):
            return {
                "schema_version": "0.1",
                "candidates": [],
                "state": {"calls": previous["calls"] + 1},
                "events": [],
                "action_proposals": [],
            }
        if self.variant == "B0":
            return {
                "schema_version": "0.1",
                "candidates": [],
                "state": {"calls": 1},
                "action_proposals": [],
                "events": [
                    {
                        "type": "a5.memory_card_decision",
                        "variant": "B0",
                        "status": "not_selected",
                        "items": [],
                    }
                ],
            }
        pool = self.cards
        if self.variant == "B2":
            pool = tuple(card for card in self.cards if card.verification_status == "validated_fix")
        ranked = rank_cards(
            pool, repo=self.repo, issue=self.issue, min_score=self.min_score
        )
        candidates, decisions = [], []
        remaining = self.max_bytes
        for score, card in ranked:
            validity = "not_checked"
            reason = "variant_without_gate"
            if self.variant == "B3":
                result = check_card_dependencies(card.dependencies, self.target_root)
                validity = result.status
                detail = ";".join(check.reason for check in result.checks)
                reason = ",".join((*validity_reasons(result), detail))
                if validity == "invalid":
                    decisions.append(
                        {
                            "source_id": card.source_id,
                            "status": "rejected_invalid",
                            "reason": reason,
                            "bytes": 0,
                            "score": round(score, 4),
                        }
                    )
                    continue
            text = raw_trajectory_text(card) if self.variant == "B1" else render_card(card)
            size = len(text.encode("utf-8"))
            if size > remaining:
                decisions.append(
                    {
                        "source_id": card.source_id,
                        "status": "over_budget",
                        "reason": reason,
                        "bytes": size,
                        "score": round(score, 4),
                    }
                )
                continue
            remaining -= size
            decisions.append(
                {
                    "source_id": card.source_id,
                    "status": "selected",
                    "reason": reason,
                    "bytes": size,
                    "score": round(score, 4),
                }
            )
            candidates.append(
                {
                    "id": card.source_id,
                    "text": text,
                    "source": card.source_id,
                    "reason": "memory_card",
                    "valid": validity in {"valid", "not_checked", "unknown"},
                    "priority": 0,
                    "repo_revision": policy_input.get("repo_revision"),
                }
            )
        if not ranked:
            overall = "no_relevant_memory"
        elif candidates:
            overall = "selected"
        elif any(item["status"] == "rejected_invalid" for item in decisions):
            overall = "rejected_invalid"
        else:
            overall = "not_selected"
        return {
            "schema_version": "0.1",
            "candidates": candidates,
            "state": {"calls": 1},
            "action_proposals": [],
            "events": [
                {
                    "type": "a5.memory_card_decision",
                    "variant": self.variant,
                    "status": overall,
                    "items": decisions,
                }
            ],
        }
