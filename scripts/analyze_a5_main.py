"""Pre-registered A5-main analysis. Section 6 of the design note.

This script reads a JSONL summary the caller passes in. It does not look for R6 runs.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

SEED = 20260926
PERMUTATIONS = 10000
DETECTION_Z = 2.8
DETECTION_SD = 0.35


def detection_floor_points(n_tasks: int) -> float:
    if n_tasks <= 0:
        return 0.0
    return 100.0 * DETECTION_Z * DETECTION_SD / math.sqrt(n_tasks)


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def sign_flip_p(values: list[float], *, n: int = PERMUTATIONS, seed: int = SEED) -> float:
    observed = abs(_mean(values))
    rng = random.Random(seed)
    extreme = 0
    for _ in range(n):
        sample = [value if rng.randrange(2) else -value for value in values]
        if abs(_mean(sample)) >= observed - 1e-12:
            extreme += 1
    return extreme / n


def bootstrap_ci(values: list[float], *, n: int = PERMUTATIONS, seed: int = SEED) -> tuple[float, float]:
    rng = random.Random(seed + 1)
    means = []
    size = len(values)
    for _ in range(n):
        draw = [values[rng.randrange(size)] for _ in range(size)]
        means.append(_mean(draw))
    means.sort()
    low = means[math.floor(0.025 * (n - 1))]
    high = means[math.ceil(0.975 * (n - 1))]
    return low, high


def _injected_count(row: dict) -> int:
    memory = row.get("memory") or {}
    injected = memory.get("injected", row.get("memory.injected", 0))
    if isinstance(injected, list):
        return len(injected)
    return int(injected or 0)


def _rate(rows: list[dict]) -> tuple[int, int, float]:
    counted = [row for row in rows if row.get("status") != "infra_error"]
    solved = sum(1 for row in counted if row.get("solved"))
    return solved, len(counted), solved / 3.0


def prepare(rows: list[dict]) -> tuple[list[dict], list[str]]:
    by_task: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        if row.get("variant") not in {"B0", "B2"}:
            continue
        by_task[row["task_id"]][row["variant"]].append(row)
    eligible = []
    excluded = []
    for task_id, groups in sorted(by_task.items()):
        b0_k, b0_n, b0_rate = _rate(groups.get("B0", []))
        b2_k, b2_n, b2_rate = _rate(groups.get("B2", []))
        if b0_n < 2 or b2_n < 2:
            excluded.append(f"{task_id} B0有效{b0_n} B2有效{b2_n}")
            continue
        repo = next(row.get("repo") for row in groups["B0"] + groups["B2"] if row.get("repo"))
        injected = any(_injected_count(row) >= 1 for row in groups["B2"] if row.get("status") != "infra_error")
        eligible.append(
            {
                "task_id": task_id,
                "repo": repo,
                "b0_k": b0_k,
                "b2_k": b2_k,
                "d": b2_rate - b0_rate,
                "injected": injected,
                "b0_rows": [row for row in groups["B0"] if row.get("status") != "infra_error"],
                "b2_rows": [row for row in groups["B2"] if row.get("status") != "infra_error"],
            }
        )
    return eligible, excluded


def _stats(tasks: list[dict]) -> dict:
    values = [task["d"] for task in tasks]
    if not values:
        return {"n": 0, "mean": 0.0, "p": 1.0, "low": 0.0, "high": 0.0, "floor": 0.0}
    low, high = bootstrap_ci(values)
    return {
        "n": len(values),
        "mean": _mean(values),
        "p": sign_flip_p(values),
        "low": low,
        "high": high,
        "floor": detection_floor_points(len(values)),
    }


def _conclusion(stats: dict) -> str:
    if stats["n"] == 0:
        return "没有合格的题，不能下结论。"
    mean_pp = 100.0 * stats["mean"]
    low_pp = 100.0 * stats["low"]
    high_pp = 100.0 * stats["high"]
    if stats["low"] <= 0.0 <= stats["high"]:
        return f"没有检出大于 {stats['floor']:.1f} 个百分点的效应"
    return f"平均 d_t 为 {mean_pp:.1f} 个百分点（95% 区间 {low_pp:.1f} 到 {high_pp:.1f}）"


def _metric(rows: list[dict], key: str) -> float | None:
    values = []
    for row in rows:
        value = row.get(key)
        if isinstance(value, (int, float)):
            values.append(float(value))
    if not values:
        return None
    return _mean(values)


def short_groups(rows: list[dict]) -> list[str]:
    """List B0 or B2 groups that are not three runs. Do not invent the missing ones."""
    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in rows:
        if row.get("variant") in {"B0", "B2"}:
            counts[str(row.get("task_id"))][row["variant"]] += 1
    notes = []
    for task_id, groups in sorted(counts.items()):
        for variant in ("B0", "B2"):
            count = groups.get(variant, 0)
            if count != 3:
                notes.append(f"{task_id} {variant} {count}/3")
    return notes


def render_report(rows: list[dict]) -> str:
    eligible, excluded = prepare(rows)
    incomplete = short_groups(rows)
    primary = _stats(eligible)
    secondary_tasks = [task for task in eligible if task["injected"]]
    secondary = _stats(secondary_tasks)
    lines = [
        "# A5-main 分析",
        "",
        "解出率是非 infra_error 运行里的解出次数除以 3。有效运行少于 2 次的题不进入主要分析。",
        f"置换检验和 bootstrap 各 {PERMUTATIONS} 次，种子 {SEED}。",
        "",
        "## 逐题",
        "",
        "| 题 | 仓库 | B0 | B2 | d_t | B2 注入 |",
        "|---|---|---|---|---|---|",
    ]
    for task in eligible:
        lines.append(
            f"| {task['task_id']} | {task['repo']} | {task['b0_k']}/3 | {task['b2_k']}/3 | {task['d']:.3f} | {task['injected']} |"
        )
    lines.extend(["", "## 剔除", ""])
    lines.append("、".join(excluded) if excluded else "无")
    lines.extend(["", "## 不满 3 次", ""])
    lines.append("、".join(incomplete) if incomplete else "无")
    lines.extend(
        [
            "",
            "## 主要分析",
            "",
            f"- 题数：{primary['n']}",
            f"- 平均 d_t：{primary['mean']:.4f}",
            f"- 双侧符号翻转 p：{primary['p']:.4f}",
            f"- 95% 区间：{primary['low']:.4f} 到 {primary['high']:.4f}",
            f"- 结论：{_conclusion(primary)}",
            "",
            "## 次要分析",
            "",
            f"- 注入了至少 1 张卡的题数：{secondary['n']}",
            f"- 平均 d_t：{secondary['mean']:.4f}",
            f"- 双侧符号翻转 p：{secondary['p']:.4f}",
            f"- 95% 区间：{secondary['low']:.4f} 到 {secondary['high']:.4f}",
            f"- 结论：{_conclusion(secondary)}",
            "",
            "### 按仓库",
            "",
        ]
    )
    by_repo: dict[str, list[dict]] = defaultdict(list)
    for task in secondary_tasks:
        by_repo[task["repo"]].append(task)
    if not by_repo:
        lines.append("无")
    for repo, tasks in sorted(by_repo.items()):
        lines.append(f"- {repo}：{len(tasks)} 题，平均 d_t {_mean([task['d'] for task in tasks]):.4f}")
    lines.extend(["", "## 花费和过程", ""])

    def side(name: str, key: str) -> str:
        b0 = [row for task in eligible for row in task["b0_rows"]]
        b2 = [row for task in eligible for row in task["b2_rows"]]
        left = _metric(b0, key)
        right = _metric(b2, key)
        left_text = "无" if left is None else f"{left:.3f}"
        right_text = "无" if right is None else f"{right:.3f}"
        return f"- {name}：B0 {left_text}，B2 {right_text}"

    lines.append(side("花费 CNY", "cost_cny"))
    lines.append(side("模型调用次数", "model_calls"))
    lines.append(side("第一次编辑轮次", "first_edit_step"))
    lines.append("")
    return "\n".join(lines)


def load_rows(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _reject_mock(payload: dict, label: str) -> None:
    scope = str(payload.get("scope") or "")
    if scope in {"mock", "step7-mock"} or payload.get("mock") is True:
        raise ValueError("mock_input:" + label)


def _repo_from_task(task_id: str) -> str:
    if "__" not in task_id:
        return ""
    owner, rest = task_id.split("__", 1)
    name = rest.rsplit("-", 1)[0]
    return f"{owner}/{name}"


def _number(value: object) -> object:
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return value
    return value


def load_a5_main_tree(root: Path) -> list[dict]:
    """Read runs/a5-main/<task>/<b0|b2>/r<k>/summary.json. Do not fill missing repeats."""
    if not root.is_dir():
        raise ValueError("a5_main_root_missing")
    rows = []
    for task_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        for dirname, variant in (("b0", "B0"), ("b2", "B2")):
            variant_dir = task_dir / dirname
            if not variant_dir.is_dir():
                continue
            for run_dir in sorted(path for path in variant_dir.glob("r*") if path.is_dir()):
                summary_path = run_dir / "summary.json"
                if not summary_path.is_file():
                    continue
                summary = json.loads(summary_path.read_text(encoding="utf-8"))
                _reject_mock(summary, summary_path.name)
                task_id = str(summary.get("task_id") or task_dir.name)
                rows.append(
                    {
                        "task_id": task_id,
                        "repo": summary.get("repo") or _repo_from_task(task_id),
                        "variant": summary.get("variant") or variant,
                        "repeat": summary.get("repeat") or int(run_dir.name[1:]),
                        "solved": summary.get("solved"),
                        "status": summary.get("status"),
                        "cost_cny": _number(summary.get("cost_cny")),
                        "model_calls": summary.get("model_calls"),
                        "first_edit_step": summary.get("first_edit_step"),
                        "memory": summary.get("memory") or {},
                    }
                )
    return rows


def load_main_b0_handoff(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    _reject_mock(data, path.name)
    if data.get("schema") != "sprint6.main-b0-runs.v1":
        raise ValueError("unexpected_main_b0_schema")
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=Path)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--b0-handoff", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.runs is None and args.root is None:
        print("STOP need --runs or --root")
        return 2
    try:
        rows = load_rows(args.runs) if args.runs else []
        if args.root:
            rows.extend(load_a5_main_tree(args.root))
        if args.b0_handoff:
            load_main_b0_handoff(args.b0_handoff)
    except ValueError as exc:
        print("STOP", exc)
        return 2
    report = render_report(rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report, encoding="utf-8")
    print(args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
