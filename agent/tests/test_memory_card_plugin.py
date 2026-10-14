import asyncio
from pathlib import Path

from reposkill_agent.memory.card_plugin import MemoryCardPlugin
from reposkill_agent.memory.records import CardDependency, MemoryCard

REPO = "demo/demo"


def card(
    source_id: str,
    *,
    repo: str = REPO,
    summary: str,
    files: tuple[str, ...],
    symbol: str,
    verification_status: str = "validated_fix",
) -> MemoryCard:
    return MemoryCard(
        repo=repo,
        created_at="2020-01-01T00:00:00+00:00",
        version="abc123def456",
        source_id=source_id,
        issue_summary=summary,
        relevant_files=files,
        fix_approach=f"Edited {files[0]} to adjust {symbol}.",
        verification_status=verification_status,
        dependencies=(CardDependency(path=files[0], symbols=(symbol,)),),
        observations=("looked around",),
        actions=(f"search_replace:{files[0]}",),
        public_verification="smoke",
    )


def plugin(variant: str, cards, issue: str, root: Path, **kwargs) -> MemoryCardPlugin:
    return MemoryCardPlugin(
        variant=variant,
        cards=tuple(cards),
        repo=REPO,
        issue=issue,
        target_root=root,
        **kwargs,
    )


def decide(variant, cards, issue, root, **kwargs):
    return asyncio.run(plugin(variant, cards, issue, root, **kwargs).decide({}))


def test_b0_injects_nothing(tmp_path):
    cards = [card("alpha", summary="alpha widget parser", files=("pkg/alpha.py",), symbol="parse")]
    result = decide("B0", cards, "alpha widget parser pkg/alpha.py", tmp_path)
    assert result["candidates"] == []
    assert result["events"][0]["status"] == "not_selected"


def test_b1_and_b2_select_the_same_sources(tmp_path):
    cards = [
        card("alpha", summary="alpha widget parser fails on empty input", files=("pkg/alpha.py",), symbol="parse"),
        card("beta", summary="beta cache eviction", files=("pkg/beta.py",), symbol="evict"),
        card("other", repo="other/other", summary="alpha widget parser", files=("pkg/alpha.py",), symbol="parse"),
    ]
    issue = "alpha widget parser fails when pkg/alpha.py sees empty input"
    b1 = decide("B1", cards, issue, tmp_path)
    b2 = decide("B2", cards, issue, tmp_path)
    assert [item["id"] for item in b1["candidates"]] == [item["id"] for item in b2["candidates"]]
    assert b1["candidates"][0]["id"] == "alpha"
    assert b1["candidates"][0]["text"] != b2["candidates"][0]["text"]
    assert "historical_issue" in b1["candidates"][0]["text"]
    assert b2["candidates"][0]["text"].startswith("[historical attempt")


def test_b2_drops_failed_and_unverified(tmp_path):
    cards = [
        card("failed", summary="alpha widget parser fails on empty input", files=("pkg/alpha.py",), symbol="parse", verification_status="failed_attempt"),
        card("raw", summary="alpha widget parser fails on empty input", files=("pkg/alpha.py",), symbol="parse", verification_status="unverified"),
        card("ok", summary="alpha widget parser fails on empty input", files=("pkg/alpha.py",), symbol="parse", verification_status="validated_fix"),
    ]
    issue = "alpha widget parser fails when pkg/alpha.py sees empty input"
    b2 = decide("B2", cards, issue, tmp_path)
    b1 = decide("B1", cards, issue, tmp_path)
    assert [item["id"] for item in b2["candidates"]] == ["ok"]
    assert {item["id"] for item in b1["candidates"]} == {"failed", "raw", "ok"}


def test_b3_rejects_deleted_symbol(tmp_path):
    target = tmp_path / "pkg"
    target.mkdir()
    (target / "alpha.py").write_text("def other():\n    return 1\n", encoding="utf-8")
    cards = [card("alpha", summary="alpha widget parser", files=("pkg/alpha.py",), symbol="parse")]
    result = decide("B3", cards, "alpha widget parser in pkg/alpha.py", tmp_path)
    assert result["candidates"] == []
    assert result["events"][0]["items"][0]["status"] == "rejected_invalid"
    assert "symbol_missing" in result["events"][0]["items"][0]["reason"]


def test_low_score_selects_nothing(tmp_path):
    cards = [card("alpha", summary="alpha widget parser", files=("pkg/alpha.py",), symbol="parse")]
    result = decide("B2", cards, "zzzzqqqq unrelated", tmp_path)
    assert result["candidates"] == []
    assert result["events"][0]["status"] == "no_relevant_memory"


def test_injection_stays_within_byte_cap(tmp_path):
    cards = [
        card("alpha", summary="alpha widget parser " + ("detail " * 40), files=("pkg/alpha.py",), symbol="parse"),
        card("alpha2", summary="alpha widget parser extra", files=("pkg/alpha.py",), symbol="parse"),
    ]
    result = decide(
        "B2",
        cards,
        "alpha widget parser pkg/alpha.py",
        tmp_path,
        max_bytes=400,
        min_score=0.1,
    )
    total = sum(len(item["text"].encode("utf-8")) for item in result["candidates"])
    assert total <= 400
    assert any(item["status"] == "over_budget" for item in result["events"][0]["items"])
