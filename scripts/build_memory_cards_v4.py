"""Build memory-cards-v4. Uses the harness handoff when it exists, else sprint2-b0."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from reposkill_agent.memory.cards import render_card
from reposkill_agent.memory.cards_v4 import (
    PilotTargetInSources,
    build_memory_cards_v4,
    cards_jsonl,
    file_sha256,
    interim_runs,
    load_handoff_runs,
    manifest_for,
)

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "configs" / "a5" / "canonical-handoff.json"
SNAPSHOT = Path(
    "D:/crq/src/coding-harness/docs/upgrade/evidence/"
    "A5-real240-77-harness-preflight/memory-snapshot.jsonl"
)
VERIFICATION = Path("D:/crq/src/coding-harness/docs/sprint/memory-source-verification.json")
HANDOFF = Path("D:/crq/src/coding-harness/docs/sprint/memory-source-runs.json")
SPRINT = Path("D:/crq/src/coding-harness/runs/sprint2-b0")
CARDS_PATH = ROOT / "benchmarks" / "a5" / "memory-cards-v4.jsonl"
MANIFEST_PATH = ROOT / "benchmarks" / "a5" / "memory-cards-v4.manifest.json"
PROTOCOL_PATH = ROOT / "docs" / "sprint" / "MEMORY-PROTOCOL-V4.md"
RENDER_PATH = ROOT / "docs" / "sprint" / "V4-CARDS.md"


def main() -> int:
    if HANDOFF.is_file():
        runs = load_handoff_runs(HANDOFF)
        status = "final"
        runs_sha = file_sha256(HANDOFF)
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
        )
    except PilotTargetInSources as exc:
        print("STOP pilot target id in memory sources:", exc)
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
                "3. 新环境下没有运行时，用旧记忆池轨迹，标签来自 `memory-source-verification.json`；grader 不可用则为 `unverified`，`label_origin=legacy_verification`。",
                "",
                "和 v3 的差别：目录兼容 sprint 布局；`changed` 支持 base64；失败尝试不渲染 approach；",
                "只保留真正的测试命令；记忆源扩到 15 道（缺运行的先不编造卡片）。",
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
