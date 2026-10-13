"""Pre-registered A6-R analysis. docs/sprint/A6-R-PREREG.zh-CN.md.

Reads the harness a6-retry-runs.json and a6-attempts.json. Second-attempt and first-attempt
diffs come from candidate-delta.json under the harness root. grader-result.json is never read.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.a6_diff import diff_against, is_test_path, load_delta  # noqa: E402
from scripts.handoff_sha import handoff_sha256  # noqa: E402

SEED = 20261013
PERMUTATIONS = 10000
DETECTION_Z = 2.8
DETECTION_SD = 0.35
FULL_CALLS = 40
SCHEMA = "a6.retry-runs.v1"
EXPECTED_FIRSTS = 53
EXPECTED_TASKS = 22
ARMS = ("r0", "r1")
REPEATS = (1, 2, 3)
TRIGGER = 0.05
POWER_LINE = (
    "事先算好的功效（OPTIONS 模拟，假设每次失败运行同一加性提升）："
    "+10pp 约 54%，+15pp 约 85%，+20pp 约 98%。"
)
_FIRST = re.compile(r"b0r([123])")
_RETIRED = re.compile(r"\.infra[0-9]+$")


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


def bootstrap_ci(
    values: list[float], *, n: int = PERMUTATIONS, seed: int = SEED
) -> tuple[float, float]:
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


def _reject_mock(payload: dict, label: str) -> None:
    scope = str(payload.get("scope") or "")
    if scope in {"mock", "step7-mock"} or payload.get("mock") is True:
        raise ValueError("mock_input:" + label)


def _valid(row: dict) -> bool:
    return row.get("status") != "infra_error"


def _number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def load_runs(path: Path) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    _reject_mock(payload, Path(path).name)
    if payload.get("schema") != SCHEMA:
        raise ValueError("unexpected_runs_schema")
    runs = payload.get("runs")
    if not isinstance(runs, list):
        raise ValueError("runs_not_a_list")
    for row in runs:
        if row.get("mock") is not False:
            raise ValueError("mock_input:" + str(row.get("run_dir")))
        if row.get("arm") not in ARMS:
            raise ValueError("unexpected_arm:" + str(row.get("arm")))
    return payload


def load_attempts(path: Path) -> list[dict]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    _reject_mock(payload, Path(path).name)
    items = payload.get("attempts")
    if not isinstance(items, list):
        items = payload.get("records")
    if not isinstance(items, list):
        raise ValueError("attempts_not_a_list")
    attempts = []
    for item in items:
        task = str(item.get("task") or item.get("task_id") or "")
        first = str(item.get("first") or "")
        if not task or _FIRST.fullmatch(first) is None:
            raise ValueError("bad_attempt_entry:" + task + ":" + first)
        attempts.append({"task": task, "first": first, "sha256": item.get("sha256")})
    return attempts


def _rate(rows: list[dict]) -> tuple[int, int, float]:
    counted = [row for row in rows if _valid(row)]
    solved = sum(1 for row in counted if row.get("solved"))
    n_valid = len(counted)
    return solved, n_valid, (solved / n_valid if n_valid else 0.0)


def prepare(rows: list[dict]) -> tuple[list[dict], list[str]]:
    by_task: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        by_task[str(row["task_id"])][row["arm"]].append(row)
    eligible = []
    excluded = []
    for task_id, groups in sorted(by_task.items()):
        r0_k, r0_n, r0_rate = _rate(groups.get("r0", []))
        r1_k, r1_n, r1_rate = _rate(groups.get("r1", []))
        if r0_n < 2 or r1_n < 2:
            excluded.append(f"{task_id} R0有效{r0_n} R1有效{r1_n}")
            continue
        repo = next((row.get("repo") for row in groups["r0"] + groups["r1"] if row.get("repo")), "")
        eligible.append(
            {
                "task_id": task_id,
                "repo": repo,
                "r0_k": r0_k,
                "r0_n": r0_n,
                "r1_k": r1_k,
                "r1_n": r1_n,
                "d": r1_rate - r0_rate,
                "rows": {arm: [row for row in groups.get(arm, []) if _valid(row)] for arm in ARMS},
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


def detected(stats: dict) -> bool:
    return stats["n"] > 0 and stats["p"] < 0.05 and (stats["low"] > 0.0 or stats["high"] < 0.0)


def conclusion(stats: dict) -> str:
    if stats["n"] == 0:
        return "没有合格的题，不能下结论。"
    mean_pp = 100.0 * stats["mean"]
    low_pp = 100.0 * stats["low"]
    high_pp = 100.0 * stats["high"]
    if detected(stats):
        return (
            f"检出效应：平均 d_t 为 {mean_pp:.1f} 个百分点"
            f"（95% 区间 {low_pp:.1f} 到 {high_pp:.1f}，p = {stats['p']:.4f}）"
        )
    return (
        f"未检出大于 {stats['floor']:.1f} 个百分点的效应。"
        f"点估计 {mean_pp:.1f} 个百分点，95% 区间 {low_pp:.1f} 到 {high_pp:.1f}"
    )


def second_stage_triggered(stats: dict) -> bool:
    return stats["n"] > 0 and stats["mean"] >= TRIGGER and stats["low"] <= 0.0 <= stats["high"]


def slot_issues(rows: list[dict], attempts: list[dict]) -> dict[str, list[str]]:
    expected = {
        (item["task"], arm, item["first"], k) for item in attempts for arm in ARMS for k in REPEATS
    }
    seen: dict[tuple, int] = defaultdict(int)
    wrong_dir = []
    for row in rows:
        key = (str(row["task_id"]), row["arm"], str(row.get("first")), row.get("k"))
        seen[key] += 1
        want = f"runs/a6-retry/{key[0]}/{key[1]}/{key[2]}/r{key[3]}"
        if str(row.get("run_dir") or "").replace("\\", "/") != want:
            wrong_dir.append(f"{'/'.join(map(str, key))} -> {row.get('run_dir')}")
    shas = {(item["task"], item["first"]): item["sha256"] for item in attempts}
    sha_mismatch = []
    for row in rows:
        if row["arm"] != "r1":
            continue
        key = (str(row["task_id"]), str(row.get("first")))
        got = (row.get("retry") or {}).get("attempt_sha256")
        if key in shas and got != shas[key]:
            sha_mismatch.append(f"{key[0]}/{key[1]}/r{row.get('k')}")

    def fmt(key: tuple) -> str:
        return f"{key[0]}/{key[1]}/{key[2]}/r{key[3]}"

    return {
        "缺的槽位": sorted(fmt(key) for key in expected - set(seen)),
        "重复的槽位": sorted(fmt(key) for key, count in seen.items() if count > 1),
        "清单外的槽位": sorted(fmt(key) for key in set(seen) - expected),
        "run_dir 与槽位不符": sorted(wrong_dir),
        "R1 的 attempt_sha256 与清单不符": sorted(sha_mismatch),
    }


class FirstAttempts:
    """Read-only access to A5 B0 run directories and the original source."""

    def __init__(self, harness_root: Path):
        self.root = Path(harness_root)
        self._summaries: dict[tuple[str, int], dict] = {}
        self._diffs: dict[tuple[str, str], str] = {}

    def original(self, task: str) -> Path:
        return self.root / "runs" / "sprint5-main-images" / task / "staging" / "original"

    def summary(self, task: str, repeat: int) -> dict:
        key = (task, repeat)
        if key not in self._summaries:
            path = self.root / "runs" / "a5-main" / task / "b0" / f"r{repeat}" / "summary.json"
            summary = json.loads(path.read_text(encoding="utf-8"))
            _reject_mock(summary, str(path))
            self._summaries[key] = summary
        return self._summaries[key]

    def first_summary(self, task: str, first: str) -> dict:
        return self.summary(task, int(first[len("b0r") :]))

    def first_diff(self, task: str, first: str) -> str:
        key = (task, first)
        if key not in self._diffs:
            run_dir = self.root / "runs" / "a5-main" / task / "b0" / ("r" + first[len("b0r") :])
            delta = load_delta(run_dir)
            if delta is None:
                raise ValueError("first_attempt_delta_missing:" + task + "/" + first)
            self._diffs[key] = diff_against(delta, self.original(task))
        return self._diffs[key]

    def second_diff(self, task: str, run_dir: str) -> str | None:
        delta = load_delta(self.root / run_dir)
        if delta is None:
            return None
        return diff_against(delta, self.original(task))

    def tier(self, task: str) -> str:
        rows = [self.summary(task, repeat) for repeat in REPEATS]
        solved = sum(1 for row in rows if _valid(row) and row.get("solved"))
        return "0/3" if solved == 0 else "中间档"

    def b0_prompt_sha(self, task: str) -> str | None:
        return self.summary(task, 1).get("prompt_sha256")


def _non_test(files: list | None) -> set[str]:
    return {str(name) for name in files or [] if not is_test_path(str(name))}


def secondary(eligible: list[dict], firsts: FirstAttempts) -> dict[str, dict]:
    out = {}
    for arm in ARMS:
        rows = [row for task in eligible for row in task["rows"][arm]]
        same = 0
        compared = 0
        missing = []
        reused = 0
        for row in rows:
            task = str(row["task_id"])
            first = str(row["first"])
            second = firsts.second_diff(task, str(row["run_dir"]))
            if second is None:
                missing.append(str(row["run_dir"]))
            else:
                compared += 1
                if second == firsts.first_diff(task, first):
                    same += 1
            before = _non_test(firsts.first_summary(task, first).get("changed_files"))
            if _non_test(row.get("changed_files")) & before:
                reused += 1
        edits = [
            float(row["first_edit_step"])
            for row in rows
            if _number(row.get("first_edit_step")) is not None
        ]
        calls = [_number(row.get("model_calls")) for row in rows]
        calls = [value for value in calls if value is not None]
        costs = [_number(row.get("cost_cny")) for row in rows]
        costs = [value for value in costs if value is not None]
        out[arm] = {
            "runs": len(rows),
            "same": same,
            "compared": compared,
            "missing_delta": missing,
            "reused": reused,
            "edit_mean": _mean(edits) if edits else None,
            "edit_median": statistics.median(edits) if edits else None,
            "edit_null": len(rows) - len(edits),
            "calls_mean": _mean(calls) if calls else None,
            "calls_full": sum(1 for value in calls if value >= FULL_CALLS),
            "calls_n": len(calls),
            "cost_mean": _mean(costs) if costs else None,
        }
    return out


def _ratio(part: int, whole: int) -> str:
    return f"{part}/{whole}（{part / whole:.3f}）" if whole else f"{part}/0"


def _num(value: float | None, digits: int = 3) -> str:
    return "无" if value is None else f"{value:.{digits}f}"


def render_report(
    payload: dict,
    attempts: list[dict],
    harness_root: Path,
    *,
    runs_sha: str | None = None,
    attempts_sha: str | None = None,
) -> str:
    rows = [row for row in payload["runs"] if not _RETIRED.search(str(row.get("run_dir") or ""))]
    retired = [str(row.get("run_dir")) for row in payload["runs"] if row not in rows]
    firsts = FirstAttempts(harness_root)
    eligible, excluded = prepare(rows)
    primary = _stats(eligible)
    issues = slot_issues(rows, attempts)
    first_tasks = sorted({item["task"] for item in attempts})
    first_count = defaultdict(int)
    for item in attempts:
        first_count[item["task"]] += 1
    scope = str(payload.get("scope") or "")
    title = "# A6-R 分析" + ("（合成数据，scope=synthetic）" if scope == "synthetic" else "")
    declared = payload.get("attempts_sha256")
    lines = [
        title,
        "",
        f"- `a6-retry-runs.json` handoff_sha256：`{runs_sha or '未计算'}`",
        f"- `a6-attempts.json` handoff_sha256：`{attempts_sha or '未计算'}`",
        f"- runs 里记录的 `attempts_sha256`：`{declared}`"
        + (
            ""
            if attempts_sha is None
            else ("，一致" if declared == attempts_sha else "，**不一致**")
        ),
        "",
        "解出率是非 infra_error 运行里的解出次数除以有效运行数。",
        "每题每组有效运行少于 2 次的题不进入主分析。",
        f"置换检验和 bootstrap 各 {PERMUTATIONS} 次，种子 {SEED}。",
        "",
        "## 输入核对",
        "",
        f"- 第一次尝试：{len(attempts)} 次、{len(first_tasks)} 道题（预期 {EXPECTED_FIRSTS}/{EXPECTED_TASKS}）",
        f"- 槽位行数：{len(rows)}（预期 {len(attempts) * len(ARMS) * len(REPEATS)}）",
        f"- infra_error：{sum(1 for row in rows if not _valid(row))} 次",
        "- 列出的退役目录（未计入）：" + ("、".join(retired) if retired else "无"),
    ]
    for name, items in issues.items():
        lines.append(f"- {name}：" + ("、".join(items) if items else "无"))
    prompt_bad = []
    for task in first_tasks:
        r0 = {
            row.get("prompt_sha256")
            for row in rows
            if row["task_id"] == task and row["arm"] == "r0"
        }
        if r0 and r0 != {firsts.b0_prompt_sha(task)}:
            prompt_bad.append(task)
    lines.append(
        "- R0 的 prompt_sha256 与 A5 B0 不同的题："
        + ("、".join(prompt_bad) if prompt_bad else "无")
    )
    lines.extend(
        [
            "",
            "## 逐题",
            "",
            "| 题 | 仓库 | A5 B0 档位 | 第一次尝试数 | R0 | R1 | d_t |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    tiers = {}
    for task in eligible:
        tiers[task["task_id"]] = firsts.tier(task["task_id"])
        cells = [
            task["task_id"],
            task["repo"],
            tiers[task["task_id"]],
            str(first_count.get(task["task_id"], 0)),
            f"{task['r0_k']}/{task['r0_n']}",
            f"{task['r1_k']}/{task['r1_n']}",
            f"{task['d']:.3f}",
        ]
        lines.append("| " + " | ".join(cells) + " |")
    lines.extend(["", "## 剔除", "", "、".join(excluded) if excluded else "无"])
    lines.extend(
        [
            "",
            "## 主分析",
            "",
            f"- 题数：{primary['n']}",
            f"- 平均 d_t：{primary['mean']:.4f}",
            f"- 双侧符号翻转 p：{primary['p']:.4f}",
            f"- 95% 区间：{primary['low']:.4f} 到 {primary['high']:.4f}",
            f"- 设计检测下限：{primary['floor']:.1f} 个百分点（2.8×0.35/√N）",
            f"- 结论：{conclusion(primary)}",
            f"- {POWER_LINE}",
            "- 第二阶段触发（点估计 ≥ +5pp 且区间含 0）："
            + (
                "满足，允许另立 A6-R2 计划"
                if second_stage_triggered(primary)
                else "不满足，不做第二阶段"
            ),
            "",
            "## 次要指标（描述性，不做检验，不进结论句）",
            "",
            "只算进入主分析的题的有效运行。",
            "",
        ]
    )
    side = secondary(eligible, firsts)
    lines.append("### 1. diff 重复率")
    lines.append("")
    for arm in ARMS:
        item = side[arm]
        lines.append(f"- {arm.upper()}：{_ratio(item['same'], item['compared'])}")
    for arm in ARMS:
        if side[arm]["missing_delta"]:
            lines.append(
                f"- {arm.upper()} 缺 candidate-delta.json：" + "、".join(side[arm]["missing_delta"])
            )
    lines.extend(["", "### 2. 文件复用", ""])
    for arm in ARMS:
        item = side[arm]
        lines.append(f"- {arm.upper()}：{_ratio(item['reused'], item['runs'])}")
    lines.extend(["", "### 3. first_edit_step", ""])
    for arm in ARMS:
        item = side[arm]
        lines.append(
            f"- {arm.upper()}：平均 {_num(item['edit_mean'])}，中位数 {_num(item['edit_median'], 1)}，"
            f"null {item['edit_null']} 次"
        )
    lines.extend(["", "### 4. model_calls", ""])
    for arm in ARMS:
        item = side[arm]
        lines.append(
            f"- {arm.upper()}：平均 {_num(item['calls_mean'])}，"
            f"用满 {FULL_CALLS} 次 {_ratio(item['calls_full'], item['calls_n'])}"
        )
    lines.extend(["", "### 5. 花费 CNY", ""])
    for arm in ARMS:
        lines.append(f"- {arm.upper()}：平均 {_num(side[arm]['cost_mean'])}")
    lines.extend(["", "### 6. 按 A5 B0 档位（只描述，不作为效应证据）", ""])
    for name in ("0/3", "中间档"):
        group = [task["d"] for task in eligible if tiers[task["task_id"]] == name]
        if group:
            lines.append(f"- {name}：{len(group)} 题，平均 d_t {_mean(group):.4f}")
        else:
            lines.append(f"- {name}：0 题")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=Path, required=True)
    parser.add_argument("--attempts", type=Path, required=True)
    parser.add_argument("--harness-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        payload = load_runs(args.runs)
        attempts = load_attempts(args.attempts)
        report = render_report(
            payload,
            attempts,
            args.harness_root,
            runs_sha=handoff_sha256(args.runs),
            attempts_sha=handoff_sha256(args.attempts),
        )
    except (ValueError, FileNotFoundError) as exc:
        print("STOP", exc)
        return 2
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report, encoding="utf-8")
    print(args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
