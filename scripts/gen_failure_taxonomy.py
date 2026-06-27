#!/usr/bin/env python3
"""Generate failure taxonomy markdown from eval CSV exports."""

from __future__ import annotations

import argparse
import csv
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


ASSERT_PATTERNS = [
    ("command_success", re.compile(r"command_success", re.I)),
    ("command_output", re.compile(r"command_output", re.I)),
    ("file_contains", re.compile(r"file_contains", re.I)),
    ("file_not_contains", re.compile(r"file_not_contains", re.I)),
    ("multi_assert", re.compile(r"multi_assert", re.I)),
    ("file_exists", re.compile(r"file_exists", re.I)),
    ("json_equals", re.compile(r"json_equals", re.I)),
    ("regex_match", re.compile(r"regex_match", re.I)),
]


def _parse_bool(value: str) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def _assert_type(expected_failures: str) -> str:
    text = expected_failures.strip()
    if not text:
        return "unknown"
    for name, pattern in ASSERT_PATTERNS:
        if pattern.search(text):
            return name
    return "unknown"


def _truncate(text: str, limit: int = 120) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def load_failure_rows(csv_paths: list[Path]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in csv_paths:
        with path.open(encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if not _parse_bool(row.get("expected_check", "")):
                    row["_source"] = path.name
                    rows.append(row)
    return rows


def build_taxonomy(rows: list[dict[str, str]], csv_paths: list[Path]) -> str:
    total = len(rows)
    sources = [p.name for p in csv_paths]
    reason_counts: Counter[str] = Counter()
    assert_counts: Counter[str] = Counter()
    config_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"failures": 0, "total": 0})
    task_failures: Counter[tuple[str, str]] = Counter()
    task_reasons: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    task_samples: dict[tuple[str, str], str] = {}

    for row in rows:
        config = row.get("config", "unknown")
        task_id = row.get("task_id", "unknown")
        reason = (row.get("failure_reason") or "none").strip() or "none"
        reason_counts[reason] += 1
        assert_counts[_assert_type(row.get("expected_failures", ""))] += 1
        config_stats[config]["failures"] += 1
        key = (config, task_id)
        task_failures[key] += 1
        task_reasons[key][reason] += 1
        if key not in task_samples and row.get("expected_failures"):
            task_samples[key] = row["expected_failures"]

    for path in csv_paths:
        with path.open(encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                config = row.get("config", "unknown")
                config_stats[config]["total"] += 1

    lines = [
        "# Failure Taxonomy (auto-generated)",
        f"\nGenerated: {datetime.now(timezone.utc).isoformat()}",
        f"Sources: {', '.join(sources)}",
        f"\nTotal failure rows: {total}",
        "\n## By failure_reason",
        "| Reason | Count | Share |",
        "|--------|-------|-------|",
    ]
    for reason, count in reason_counts.most_common():
        share = (count / total * 100) if total else 0.0
        lines.append(f"| {reason} | {count} | {share:.1f}% |")

    lines += [
        "\n## By assert type (from expected_failures)",
        "| Assert type | Count | Share |",
        "|-------------|-------|-------|",
    ]
    for assert_type, count in assert_counts.most_common():
        share = (count / total * 100) if total else 0.0
        lines.append(f"| {assert_type} | {count} | {share:.1f}% |")

    lines += [
        "\n## By config",
        "| Config | Failures | Total rows | Fail rate |",
        "|--------|----------|------------|-----------|",
    ]
    for config in sorted(config_stats):
        stats = config_stats[config]
        fail_rate = (stats["failures"] / stats["total"] * 100) if stats["total"] else 0.0
        lines.append(
            f"| {config} | {stats['failures']} | {stats['total']} | {fail_rate:.1f}% |"
        )

    lines += [
        "\n## Representative tasks (top failures)",
        "| Task ID | Config | Count | Dominant reason | Sample expected_failure |",
        "|---------|--------|-------|-----------------|-------------------------|",
    ]
    top_tasks = sorted(task_failures.items(), key=lambda x: (-x[1], x[0][1]))[:15]
    for (config, task_id), count in top_tasks:
        dominant = task_reasons[(config, task_id)].most_common(1)[0][0]
        sample = _truncate(task_samples.get((config, task_id), ""))
        lines.append(f"| {task_id} | {config} | {count} | {dominant} | {sample} |")

    step_share = (reason_counts.get("step_limit", 0) / total * 100) if total else 0.0
    cmd_share = (assert_counts.get("command_success", 0) / total * 100) if total else 0.0
    lines += [
        "\n## Notes",
        f"- `step_limit` 占失败行 {step_share:.1f}%；scaffold 跑（更多自测步数）中撞步数墙仍常见。",
        f"- `command_success` 类 assert 失败占 {cmd_share:.1f}%，与开启 `run_command` 后 judge 跑 pytest 直接相关。",
        "- 多 config 对比时失败率差异需结合污染语境解读（见 `docs/CONTAMINATION-NOTES.zh-CN.md`）：**绝对成功率不作能力指标**。",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate failure taxonomy from eval CSVs")
    parser.add_argument("--csv", action="append", required=True, help="Eval CSV path (repeatable)")
    parser.add_argument(
        "--out",
        default="reports/examples/failure_taxonomy.md",
        help="Output markdown path",
    )
    args = parser.parse_args()

    csv_paths = [Path(p) for p in args.csv]
    for path in csv_paths:
        if not path.exists():
            raise FileNotFoundError(path)

    rows = load_failure_rows(csv_paths)
    content = build_taxonomy(rows, csv_paths)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")
    print(f"Wrote {out_path} ({len(rows)} failure rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
