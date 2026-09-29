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
    n_valid = len(counted)
    return solved, n_valid, (solved / n_valid if n_valid else 0.0)


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
                "b0_n": b0_n,
                "b2_k": b2_k,
                "b2_n": b2_n,
                "d": b2_rate - b0_rate,
                "injected": injected,
                "b0_rows": [row for row in groups["B0"] if row.get("status") != "infra_error"],
                "b2_rows": [row for row in groups["B2"] if row.get("status") != "infra_error"],
            }
        )
    return eligible, excluded


def _sample_sd(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = _mean(values)
    variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    return math.sqrt(variance)


def data_floor_points(values: list[float]) -> float:
    if not values:
        return 0.0
    return 100.0 * DETECTION_Z * _sample_sd(values) / math.sqrt(len(values))


def _stats(tasks: list[dict]) -> dict:
    values = [task["d"] for task in tasks]
    if not values:
        return {
            "n": 0,
            "mean": 0.0,
            "p": 1.0,
            "low": 0.0,
            "high": 0.0,
            "floor": 0.0,
            "data_floor": 0.0,
        }
    low, high = bootstrap_ci(values)
    return {
        "n": len(values),
        "mean": _mean(values),
        "p": sign_flip_p(values),
        "low": low,
        "high": high,
        "floor": detection_floor_points(len(values)),
        "data_floor": data_floor_points(values),
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


def _repeat(row: dict) -> int | None:
    try:
        return int(row.get("repeat"))
    except (TypeError, ValueError):
        return None


def primary_rows(rows: list[dict]) -> list[dict]:
    """Main analysis uses r1–r3 only. r4 is the drift arm."""
    return [row for row in rows if _repeat(row) in {1, 2, 3}]


def drift_diffs(rows: list[dict]) -> list[float]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if row.get("variant") == "B0":
            grouped[str(row.get("task_id"))].append(row)
    diffs = []
    for _task_id, group in sorted(grouped.items()):
        early = [
            row for row in group if _repeat(row) in {1, 2, 3} and row.get("status") != "infra_error"
        ]
        later = [row for row in group if _repeat(row) == 4 and row.get("status") != "infra_error"]
        if not early or len(later) != 1:
            continue
        early_rate = sum(1 for row in early if row.get("solved")) / len(early)
        diffs.append(float(bool(later[0].get("solved"))) - early_rate)
    return diffs


def sensitivity_diffs(rows: list[dict]) -> list[float]:
    """B2 solved/3 minus the r4 0/1 result. Descriptive only."""
    grouped: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        if row.get("variant") in {"B0", "B2"}:
            grouped[str(row.get("task_id"))][row["variant"]].append(row)
    values = []
    for _task_id, groups in sorted(grouped.items()):
        later = [
            row
            for row in groups.get("B0", [])
            if _repeat(row) == 4 and row.get("status") != "infra_error"
        ]
        b2 = [
            row
            for row in groups.get("B2", [])
            if _repeat(row) in {1, 2, 3} and row.get("status") != "infra_error"
        ]
        if len(later) != 1 or not b2:
            continue
        solved = sum(1 for row in b2 if row.get("solved"))
        values.append(solved / 3.0 - float(bool(later[0].get("solved"))))
    return values


def b0_bin(solved_count: int) -> str:
    if solved_count <= 0:
        return "0/3"
    if solved_count >= 3:
        return "3/3"
    return "1-2/3"


def load_predicted_injection(path: Path) -> dict[str, int]:
    data = json.loads(path.read_text(encoding="utf-8"))
    _reject_mock(data, path.name)
    tasks = data.get("tasks")
    if not isinstance(tasks, list):
        raise ValueError("predicted_injection_not_a_list")
    counts = {}
    for item in tasks:
        task_id = str(item.get("task_id") or "")
        cards = item.get("cards", item.get("card_ids"))
        if isinstance(cards, list):
            counts[task_id] = len(cards)
        else:
            counts[task_id] = int(item.get("predicted_cards") or 0)
    return counts


def render_report(rows: list[dict], predicted: dict[str, int] | None = None) -> str:
    main_rows = primary_rows(rows)
    eligible, excluded = prepare(main_rows)
    incomplete = short_groups(main_rows)
    primary = _stats(eligible)
    actual_tasks = [task for task in eligible if task["injected"]]
    if predicted is None:
        secondary_tasks = actual_tasks
    else:
        secondary_tasks = [task for task in eligible if predicted.get(task["task_id"], 0) >= 1]
    secondary = _stats(secondary_tasks)
    actual = _stats(actual_tasks)
    drift = drift_diffs(rows)
    drift_stats = None
    if drift:
        low, high = bootstrap_ci(drift)
        drift_stats = {"n": len(drift), "mean": _mean(drift), "low": low, "high": high}
    drifted = bool(drift_stats and (drift_stats["low"] > 0.0 or drift_stats["high"] < 0.0))
    lines = [
        "# A5-main 分析",
        "",
        "解出率是非 infra_error 运行里的解出次数除以有效运行数。",
        "有效运行少于 2 次的题不进入主要分析。",
        f"置换检验和 bootstrap 各 {PERMUTATIONS} 次，种子 {SEED}。",
        "",
        "## 逐题",
        "",
        "| 题 | 仓库 | B0 | B2 | d_t | B2 注入 |",
        "|---|---|---|---|---|---|",
    ]
    for task in eligible:
        cells = [
            task["task_id"],
            task["repo"],
            f"{task['b0_k']}/{task['b0_n']}",
            f"{task['b2_k']}/{task['b2_n']}",
            f"{task['d']:.3f}",
            str(task["injected"]),
        ]
        lines.append("| " + " | ".join(cells) + " |")
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
            f"- 设计检测下限：{primary['floor']:.1f} 个百分点（2.8×0.35/√N）",
            f"- 本次数据检测下限：{primary['data_floor']:.1f} 个百分点（2.8×s/√N）",
            f"- 结论：{_conclusion(primary)}" + ("。存在时间漂移" if drifted else ""),
            "",
            "## 次要分析",
            "",
            (
                "分组依据是处理前预测会注入至少 1 张卡的题。实际注入只用来核对。"
                if predicted is not None
                else "没有提供预测注入表，这一节暂时按实际注入至少 1 张卡分组。"
            ),
            f"- 题数：{secondary['n']}",
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
    lines.extend(["", "### 实际注入核对", ""])
    if predicted is None:
        lines.append("没有预测表，不比较。")
    else:
        predicted_ids = {task["task_id"] for task in secondary_tasks}
        actual_ids = {task["task_id"] for task in actual_tasks}
        if predicted_ids == actual_ids:
            lines.append("预测注入和实际注入的题一致。")
        else:
            lines.append("预测注入和实际注入不一致。")
            lines.append("只在预测里：" + ("、".join(sorted(predicted_ids - actual_ids)) or "无"))
            lines.append("只在实际里：" + ("、".join(sorted(actual_ids - predicted_ids)) or "无"))
    lines.append(f"- 实际注入至少 1 张卡的题数：{actual['n']}")
    lines.append(f"- 平均 d_t：{actual['mean']:.4f}")
    lines.extend(["", "## 漂移检查（描述性，非预注册）", ""])
    if drift_stats is None:
        lines.append("没有成对的 B0 r4。")
    else:
        lines.append(f"- 题数：{drift_stats['n']}")
        lines.append(f"- 平均差（r4 减 r1–r3）：{drift_stats['mean']:.4f}")
        low = drift_stats["low"]
        high = drift_stats["high"]
        lines.append(f"- 95% 区间：{low:.4f} 到 {high:.4f}")
        lines.append("不做显著性检验。")
    sensitive = sensitivity_diffs(rows)
    lines.extend(["", "### 用 r4 作同期 B0（描述性，非预注册）", ""])
    if not sensitive:
        lines.append("没有同时具备 B2 和 B0 r4 的题。")
    else:
        lines.append(f"- 题数：{len(sensitive)}")
        lines.append(f"- 平均（B2 的 k/3 减 r4）：{_mean(sensitive):.4f}")
        lines.append("不做显著性检验。")
    lines.extend(["", "## 按 B0 档位（描述性，非预注册）", ""])
    lines.append("按 B0 结果分组会受回归均值影响，不可作为效应证据。")
    bins: dict[str, list[dict]] = defaultdict(list)
    for task in eligible:
        bins[b0_bin(task["b0_k"])].append(task)
    for name in ("0/3", "1-2/3", "3/3"):
        group = bins.get(name) or []
        if not group:
            lines.append(f"- {name}：0 题")
            continue
        mean = _mean([task["d"] for task in group])
        lines.append(f"- {name}：{len(group)} 题，平均 d_t {mean:.4f}")
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
    if data.get("schema") == "sprint6.main-b0-runs.v1":
        raise ValueError("pool_v1_rejected")
    if data.get("schema") != "sprint6.main-b0-runs.v2":
        raise ValueError("unexpected_main_b0_schema")
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=Path)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--b0-handoff", type=Path)
    parser.add_argument("--predicted", type=Path)
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
        predicted = load_predicted_injection(args.predicted) if args.predicted else None
    except ValueError as exc:
        print("STOP", exc)
        return 2
    report = render_report(rows, predicted)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report, encoding="utf-8")
    print(args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
