"""Build memory-cards-v4. Uses the harness handoff when it exists, else sprint2-b0."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from reposkill_agent.memory.cards import render_card
from reposkill_agent.memory.cards_v4 import (
    PilotTargetInSources,
    assert_clean_runs,
    build_memory_cards_v4,
    cards_jsonl,
    file_sha256,
    interim_runs,
    load_handoff,
    manifest_for,
    target_ids,
)

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "configs" / "a5" / "canonical-handoff.json"
SNAPSHOT = Path(
    "D:/crq/src/coding-harness/docs/upgrade/evidence/"
    "A5-real240-77-harness-preflight/memory-snapshot.jsonl"
)
VERIFICATION = Path("D:/crq/src/coding-harness/docs/sprint/memory-source-verification.json")
HANDOFF = Path("D:/crq/src/coding-harness/docs/sprint/memory-source-runs.json")
CLEAN_IMAGES = Path("D:/crq/src/coding-harness/docs/sprint/clean-images")
SPRINT = Path("D:/crq/src/coding-harness/runs/sprint2-b0")
CARDS_PATH = ROOT / "benchmarks" / "a5" / "memory-cards-v4.jsonl"
MANIFEST_PATH = ROOT / "benchmarks" / "a5" / "memory-cards-v4.manifest.json"
PROTOCOL_PATH = ROOT / "docs" / "sprint" / "MEMORY-PROTOCOL-V4.md"
RENDER_PATH = ROOT / "docs" / "sprint" / "V4-CARDS.md"


def _published_sha256(path: Path) -> str:
    """Hash the LF form. Harness records that digest; the working copy may be CRLF."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _check_clean_images(runs: list[dict]) -> None:
    by_source: dict[str, str] = {}
    for run in runs:
        by_source.setdefault(run["source_id"], run["clean_image_digest"])
    for source_id, digest in by_source.items():
        record_path = CLEAN_IMAGES / f"{source_id}.json"
        if not record_path.is_file():
            raise ValueError("clean_image_record_missing:" + source_id)
        record = json.loads(record_path.read_text(encoding="utf-8"))
        if record.get("clean_image_digest") != digest:
            raise ValueError("clean_image_digest_mismatch:" + source_id)
        if record.get("source_only_match") is not True:
            raise ValueError("source_only_mismatch:" + source_id)
        if record.get("image_source_only_hash") != record.get("original_tree_hash"):
            raise ValueError("source_only_hash_mismatch:" + source_id)
        if not isinstance(record.get("native_artifacts"), list):
            raise ValueError("native_artifacts_missing:" + source_id)


def main() -> int:
    allow_legacy = True
    if HANDOFF.is_file():
        handoff = load_handoff(HANDOFF)
        runs = handoff["runs"]
        assert_clean_runs(runs, target_ids(CANONICAL))
        _check_clean_images(runs)
        status = "final"
        allow_legacy = False
        runs_sha = _published_sha256(HANDOFF)
    else:
        runs = interim_runs(SPRINT)
        status = "interim"
        runs_sha = None
    try:
        cards, ignored, missing = build_memory_cards_v4(
            canonical_path=CANONICAL,
            snapshot_path=SNAPSHOT,
            verification_path=VERIFICATION,
            runs=runs,
            path_base=ROOT,
            allow_legacy=allow_legacy,
        )
    except PilotTargetInSources as exc:
        print("STOP pilot target id in memory sources:", exc)
        return 2
    unexpected = [item for item in missing if item != "pytest-dev__pytest-5221"]
    if status == "final" and unexpected:
        print("STOP missing clean runs:", unexpected)
        return 2
    payload = cards_jsonl(cards)
    CARDS_PATH.write_bytes(payload)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    manifest = manifest_for(
        cards,
        payload,
        status=status,
        coding_agent_commit=commit,
        memory_source_runs_sha256=runs_sha,
        legacy_snapshot_sha256=file_sha256(SNAPSHOT),
    )
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    _write_docs(cards, status, ignored, missing)
    print(f"status={status} cards={len(cards)} ignored={ignored} missing={missing}")
    return 0


def _write_docs(cards, status: str, ignored: list[str], missing: list[str]) -> None:
    PROTOCOL_PATH.write_text(
        "\n".join(
            (
                "# v4 记忆协议",
                "",
                "标签来自源题自己的 SWE-bench 测试，由 harness grader 给出，不来自 20 道 pilot 目标题。",
                "源题和 `configs/a5/canonical-handoff.json` 的 `target_tasks` 不相交，构建时会断言。",
                "交接文件里如果出现 pilot 目标题 id，构建脚本直接停止。",
                "不在这 15 道源题里的运行会被忽略。",
                "F2P / P2P 计数只用于打标签，不写进卡片正文。",
                "",
                "选轨迹的规则是固定的，不看卡片内容：",
                "",
                "1. 新环境下有解出的运行时，取 `repeat` 最小的那一次，标 `validated_fix`，`label_origin=source_task_swebench_tests`。",
                "2. 新环境下都没解出时，取 `repeat` 最小的那一次，标 `failed_attempt`，来源同上。",
                "3. `validated_fix` 只来自 `b0-v2` 且 `answer_isolation_pass` 的 grader pass。旧轨迹和 `b0-v1` 不能标成 `validated_fix`。",
                "4. final 不用旧记忆池补洞。`pytest-5221` 不在这批 dev 运行里，所以没有卡片。",
                "",
                "和 v3 的差别：目录兼容 sprint 布局；`changed` 支持 base64；失败尝试不渲染 approach；",
                "B2 只注入 `validated_fix`；卡片来自 clean image 的运行。",
                f"这一版状态：{status}。",
                "",
            )
        ),
        encoding="utf-8",
    )
    lines = ["# v4 卡片渲染", "", f"状态：{status}。忽略的运行：{ignored or '无'}。还没有轨迹的源题：{missing or '无'}。", ""]
    for card in cards:
        lines.append(f"## {card.source_id}")
        lines.append("")
        lines.append(f"- status: {card.verification_status}")
        lines.append(f"- label_origin: {card.label_origin}")
        lines.append(f"- layout: {card.layout}")
        lines.append(f"- source_run: {card.source_run}")
        lines.append("")
        lines.append("```")
        lines.append(render_card(card))
        lines.append("```")
        lines.append("")
    RENDER_PATH.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
