"""Markdown and CSV report generation for eval results."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path

from src.eval.bootstrap import ConfidenceInterval
from src.eval.metrics import EvalMetrics, RepeatedEvalMetrics, TaskResult, is_degenerate_run
from src.eval.bootstrap import (
    bootstrap_paired_success_rate_delta_ci,
    bootstrap_proportion_ci,
)


def get_git_commit_short() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except Exception:
        return "n/a"


def config_content_hash(config: dict) -> str:
    payload = json.dumps(config, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:8]


def success_rate_by_tag(results: list[TaskResult]) -> dict[str, dict[str, float | int]]:
    stats: dict[str, dict[str, int]] = {}
    for result in results:
        tags = result.tags or ["untagged"]
        for tag in tags:
            bucket = stats.setdefault(tag, {"passed": 0, "total": 0})
            bucket["total"] += 1
            if result.success and result.expected_check:
                bucket["passed"] += 1
    return {
        tag: {
            "passed": values["passed"],
            "total": values["total"],
            "rate": (values["passed"] / values["total"] * 100) if values["total"] else 0.0,
        }
        for tag, values in sorted(stats.items())
    }


def unstable_tasks(repeated: RepeatedEvalMetrics) -> list[tuple[str, int, int]]:
    if repeated.run_count <= 1 or not repeated.runs:
        return []
    task_ids = {r.task_id for run in repeated.runs for r in run.results}
    unstable: list[tuple[str, int, int]] = []
    for task_id in sorted(task_ids):
        passes = sum(
            1
            for run in repeated.runs
            for r in run.results
            if r.task_id == task_id and r.success and r.expected_check
        )
        if 0 < passes < repeated.run_count:
            unstable.append((task_id, passes, repeated.run_count))
    return unstable


def significance_conclusion(
    ci_a: ConfidenceInterval | None,
    ci_b: ConfidenceInterval | None,
    *,
    valid_run_count_a: int | None = None,
    valid_run_count_b: int | None = None,
) -> str:
    if valid_run_count_a is not None and valid_run_count_a < 2:
        return "有效轮不足（含异常轮剔除），显著性结论 withheld，请补跑。"
    if valid_run_count_b is not None and valid_run_count_b < 2:
        return "有效轮不足（含异常轮剔除），显著性结论 withheld，请补跑。"
    if not ci_a or not ci_b:
        return "CI unavailable; cannot assess significance."
    if ci_a.high < ci_b.low or ci_b.high < ci_a.low:
        return "差异在 95% bootstrap CI 下不重叠，倾向显著。"
    return "CI 重叠，差异可能由方差导致，需更多 run。"


def format_est_cost(est_cost: float | None) -> str:
    if est_cost is None:
        return "n/a"
    return f"${est_cost:.4f}"


def per_task_pass_matrix(repeated: RepeatedEvalMetrics) -> list[tuple[str, list[str], str]]:
    if not repeated.runs:
        return []
    task_ids = sorted({r.task_id for run in repeated.runs for r in run.results})
    rows: list[tuple[str, list[str], str]] = []
    for task_id in task_ids:
        cells: list[str] = []
        passes = 0
        for run in repeated.runs:
            match = next((r for r in run.results if r.task_id == task_id), None)
            if match and match.success and match.expected_check:
                cells.append("P")
                passes += 1
            else:
                cells.append("F")
        rows.append((task_id, cells, f"{passes}/{repeated.run_count}"))
    return rows


class ReportGenerator:
    def __init__(self, output_dir: str = "reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        metrics_list: list[EvalMetrics] | list[RepeatedEvalMetrics],
        dataset_name: str = "default",
        run_metadata: dict | None = None,
    ) -> tuple[str, str]:
        """Generate Markdown and CSV reports."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        md_path = self.output_dir / f"report_{ts}.md"
        csv_path = self.output_dir / f"report_{ts}.csv"

        md_content = self._build_markdown(metrics_list, dataset_name, run_metadata)
        csv_content = self._build_csv(metrics_list)

        md_path.write_text(md_content, encoding="utf-8")
        csv_path.write_text(csv_content, encoding="utf-8")

        return str(md_path), str(csv_path)

    def _build_markdown(
        self,
        metrics_list: list[EvalMetrics] | list[RepeatedEvalMetrics],
        dataset_name: str,
        run_metadata: dict | None = None,
    ) -> str:
        if metrics_list and isinstance(metrics_list[0], RepeatedEvalMetrics):
            return self._build_repeated_markdown(metrics_list, dataset_name, run_metadata)
        return self._build_single_markdown(metrics_list, dataset_name, run_metadata)

    @staticmethod
    def _metadata_lines(run_metadata: dict | None) -> list[str]:
        if not run_metadata:
            return []
        lines = ["\n## Run Metadata\n"]
        lines.append(f"- Git commit: `{run_metadata.get('git_commit', 'n/a')}`")
        lines.append(f"- Runs: {run_metadata.get('runs', 1)}")
        lines.append(f"- Generated at: {run_metadata.get('timestamp', 'n/a')}")
        for name, info in run_metadata.get("configs", {}).items():
            lines.append(
                f"- Config `{name}`: model=`{info.get('model', 'n/a')}`, hash=`{info.get('config_hash', 'n/a')}`"
            )
        price = run_metadata.get("cost_per_1k_tokens", 0)
        lines.append(
            f"- Cost rate: {price if price else 'n/a (set --cost-per-1k to estimate)'}"
        )
        return lines

    @staticmethod
    def _tag_section(results: list[TaskResult]) -> list[str]:
        by_tag = success_rate_by_tag(results)
        if not by_tag:
            return []
        lines = ["\n## Success Rate by Tag\n", "| Tag | Passed | Total | Success Rate |", "|-----|--------|-------|--------------|"]
        for tag, stats in by_tag.items():
            lines.append(
                f"| {tag} | {stats['passed']} | {stats['total']} | {stats['rate']:.1f}% |"
            )
        return lines

    @staticmethod
    def _cost_section(metrics: EvalMetrics) -> list[str]:
        return [
            "\n## Cost Summary\n",
            f"- Total tokens: {metrics.total_tokens}",
            f"- Avg tokens/task: {metrics.avg_tokens:.0f}",
            f"- Est. cost: {format_est_cost(metrics.est_cost)}",
        ]

    @staticmethod
    def _anomalous_runs_section(metrics_list: list[RepeatedEvalMetrics]) -> list[str]:
        rows: list[tuple[str, int, EvalMetrics]] = []
        for repeated in metrics_list:
            for idx, run in enumerate(repeated.runs, start=1):
                if is_degenerate_run(run):
                    rows.append((repeated.config_name, idx, run))
        if not rows:
            return []
        lines = [
            "\n## Anomalous Runs\n",
            f"> 检测到 {len(rows)} 个异常轮（疑似 provider 故障：成功率=0 且几乎无推进/高 model_error），已从均值/方差/CI 中剔除。",
            "| Config | Run | Success Rate | Avg Steps | Model Errors | 判定 |",
            "|--------|-----|--------------|-----------|--------------|------|",
        ]
        for config_name, idx, run in rows:
            lines.append(
                f"| {config_name} | {idx} | {run.success_rate:.1f}% | "
                f"{run.avg_steps:.1f} | {run.model_error_count} | ⚠ degenerate |"
            )
        return lines

    @staticmethod
    def _valid_runs_note(repeated: RepeatedEvalMetrics) -> str:
        if repeated.degenerate_run_indices:
            return f" (有效轮 {repeated.valid_run_count}/{repeated.run_count})"
        return ""

    @staticmethod
    def _pass_matrix_section(repeated: RepeatedEvalMetrics) -> list[str]:
        rows = per_task_pass_matrix(repeated)
        if not rows or repeated.run_count <= 1:
            return []
        header = "| Task ID | " + " | ".join(f"R{i}" for i in range(1, repeated.run_count + 1)) + " | Passes |"
        sep = "|---------|" + "|".join(["---"] * repeated.run_count) + "|--------|"
        lines = [f"\n## Per-Task Pass Matrix — `{repeated.config_name}`\n", header, sep]
        for task_id, cells, summary in rows:
            lines.append(f"| {task_id} | {' | '.join(cells)} | {summary} |")
        return lines

    def _build_single_markdown(
        self,
        metrics_list: list[EvalMetrics],
        dataset_name: str,
        run_metadata: dict | None = None,
    ) -> str:
        lines = [
            f"# Eval Report - {dataset_name}",
            f"\nGenerated: {datetime.now(timezone.utc).isoformat()}",
        ]
        lines += self._metadata_lines(run_metadata)
        lines += ["\n## Summary\n",
            "| Config | Tasks | Passed | Failed | Success Rate | Avg Steps | Avg Time (ms) | Tool Fail Rate |",
            "|--------|-------|--------|--------|--------------|-----------|---------------|----------------|",
        ]

        for m in metrics_list:
            lines.append(
                f"| {m.config_name} | {m.total_tasks} | {m.passed} | {m.failed} | "
                f"{m.success_rate:.1f}% | {m.avg_steps:.1f} | {m.avg_elapsed_ms:.0f} | "
                f"{m.tool_failure_rate:.1f}% |"
            )

        if len(metrics_list) == 2:
            a, b = metrics_list
            lines += [
                "\n## Baseline vs Hardened Comparison\n",
                f"| Metric | {a.config_name} | {b.config_name} | Delta |",
                "|--------|--------------|--------------|-------|",
                f"| Success Rate | {a.success_rate:.1f}% | {b.success_rate:.1f}% | {b.success_rate - a.success_rate:+.1f}% |",
                f"| Avg Steps | {a.avg_steps:.1f} | {b.avg_steps:.1f} | {b.avg_steps - a.avg_steps:+.1f} |",
                f"| Avg Time (ms) | {a.avg_elapsed_ms:.0f} | {b.avg_elapsed_ms:.0f} | {b.avg_elapsed_ms - a.avg_elapsed_ms:+.0f} |",
                f"| Policy Blocks | {a.policy_block_count} | {b.policy_block_count} | n/a |",
                f"| Timeouts | {a.timeout_count} | {b.timeout_count} | n/a |",
                f"| Tool Errors | {a.tool_error_count} | {b.tool_error_count} | n/a |",
                f"| Model Errors | {a.model_error_count} | {b.model_error_count} | n/a |",
            ]
            lines += self._bootstrap_single_run_section(a, b)

        for m in metrics_list:
            lines += self._tag_section(m.results)
            lines += self._cost_section(m)

        lines.append("\n## Failure Breakdown\n")
        for m in metrics_list:
            lines.append(f"### {m.config_name}\n")
            fb = m.failure_breakdown
            lines.append(f"- Timeout: {fb['timeout']}")
            lines.append(f"- Tool Error: {fb['tool_error']}")
            lines.append(f"- Policy Block: {fb['policy_block']}")
            lines.append(f"- Model Parse Error: {fb['model_parse_error']}")
            lines.append(f"- Step Limit: {fb['step_limit']}")
            lines.append("")

        lines.append("## Per-Task Results\n")
        for m in metrics_list:
            lines.append(f"### {m.config_name}\n")
            lines.append(
                "| Task ID | Expected Check | Steps | Time (ms) | Tokens | Tool Fails | Policy Blocks | Failure | Failure Detail |"
            )
            lines.append(
                "|---------|----------------|-------|-----------|--------|------------|---------------|---------|----------------|"
            )
            for r in m.results:
                status = "PASS" if r.expected_check else "FAIL"
                detail = "; ".join(r.expected_failures) if r.expected_failures else ""
                lines.append(
                    f"| {r.task_id} | {status} | {r.steps} | "
                    f"{r.elapsed_ms:.0f} | {r.tokens} | {r.tool_failures} | {r.policy_blocks} | "
                    f"{r.failure_reason.value} | {detail} |"
                )

        return "\n".join(lines)

    def _build_repeated_markdown(
        self,
        metrics_list: list[RepeatedEvalMetrics],
        dataset_name: str,
        run_metadata: dict | None = None,
    ) -> str:
        lines = [
            f"# Eval Report - {dataset_name}",
            f"\nGenerated: {datetime.now(timezone.utc).isoformat()}",
        ]
        lines += self._metadata_lines(run_metadata)
        lines += ["\n## Repeated Run Summary\n",
            "| Config | Runs | Tasks | Success Rate mean/std | Avg Steps mean/std | Avg Time mean/std (ms) | Tool Fail Rate mean/std | Policy Blocks mean/std |",
            "|--------|------|-------|-----------------------|--------------------|------------------------|-------------------------|------------------------|",
        ]

        for m in metrics_list:
            valid_note = self._valid_runs_note(m)
            lines.append(
                f"| {m.config_name} | {m.run_count}{valid_note} | {m.total_tasks} | "
                f"{m.success_rate.mean:.1f}% / {m.success_rate.std:.1f} | "
                f"{m.avg_steps.mean:.1f} / {m.avg_steps.std:.1f} | "
                f"{m.avg_elapsed_ms.mean:.0f} / {m.avg_elapsed_ms.std:.0f} | "
                f"{m.tool_failure_rate.mean:.1f}% / {m.tool_failure_rate.std:.1f} | "
                f"{m.policy_block_count.mean:.1f} / {m.policy_block_count.std:.1f} |"
            )

        if len(metrics_list) == 2:
            a, b = metrics_list
            lines += [
                "\n## Mean Delta Comparison\n",
                f"| Metric | {a.config_name} | {b.config_name} | Delta |",
                "|--------|--------------|--------------|-------|",
                f"| Success Rate | {a.success_rate.mean:.1f}% | {b.success_rate.mean:.1f}% | {b.success_rate.mean - a.success_rate.mean:+.1f}% |",
                f"| Avg Steps | {a.avg_steps.mean:.1f} | {b.avg_steps.mean:.1f} | {b.avg_steps.mean - a.avg_steps.mean:+.1f} |",
                f"| Avg Time (ms) | {a.avg_elapsed_ms.mean:.0f} | {b.avg_elapsed_ms.mean:.0f} | {b.avg_elapsed_ms.mean - a.avg_elapsed_ms.mean:+.0f} |",
                f"| Tool Fail Rate | {a.tool_failure_rate.mean:.1f}% | {b.tool_failure_rate.mean:.1f}% | {b.tool_failure_rate.mean - a.tool_failure_rate.mean:+.1f}% |",
            ]
            lines += self._model_matrix_section(metrics_list, run_metadata)
            lines += self._bootstrap_repeated_run_section(a, b)

        lines += self._anomalous_runs_section(metrics_list)

        unstable: list[tuple[str, str, int, int]] = []
        for m in metrics_list:
            for task_id, passes, runs in unstable_tasks(m):
                unstable.append((m.config_name, task_id, passes, runs))
        if unstable:
            lines.append("\n## Unstable Tasks\n")
            lines.append("| Config | Task ID | Passes | Runs |")
            lines.append("|--------|---------|--------|------|")
            for config_name, task_id, passes, runs in unstable:
                lines.append(f"| {config_name} | {task_id} | {passes} | {runs} |")

        if metrics_list and metrics_list[0].runs:
            lines += self._tag_section(metrics_list[0].runs[0].results)
            lines += self._cost_section(metrics_list[0].runs[0])

        for m in metrics_list:
            lines += self._pass_matrix_section(m)

        lines.append("\n## Per-Run Results\n")
        for m in metrics_list:
            lines.append(f"### {m.config_name}\n")
            lines.append(
                "| Run | Passed | Failed | Success Rate | Avg Steps | Avg Time (ms) | Tool Fail Rate | Policy Blocks | Note |"
            )
            lines.append(
                "|-----|--------|--------|--------------|-----------|---------------|----------------|---------------|------|"
            )
            for idx, run in enumerate(m.runs, start=1):
                note = "⚠ degenerate" if is_degenerate_run(run) else ""
                lines.append(
                    f"| {idx} | {run.passed} | {run.failed} | {run.success_rate:.1f}% | "
                    f"{run.avg_steps:.1f} | {run.avg_elapsed_ms:.0f} | "
                    f"{run.tool_failure_rate:.1f}% | {run.policy_block_count} | {note} |"
                )
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _model_matrix_section(
        metrics_list: list[RepeatedEvalMetrics],
        run_metadata: dict | None,
    ) -> list[str]:
        if len(metrics_list) < 2 or not run_metadata:
            return []
        configs_meta = run_metadata.get("configs", {})
        models = {
            info.get("model")
            for info in configs_meta.values()
            if info.get("model") and info.get("model") != "n/a"
        }
        if len(models) < 2:
            return []
        lines = [
            "\n## Model Matrix\n",
            "| Config | Model | Success Rate mean | Avg Steps | Avg Time (ms) | Total Tokens |",
            "|--------|-------|-------------------|-----------|---------------|--------------|",
        ]
        for m in metrics_list:
            model = configs_meta.get(m.config_name, {}).get("model", "n/a")
            total_tokens = sum(run.total_tokens for run in m.runs)
            if m.valid_run_count == 0 and m.runs and all(is_degenerate_run(run) for run in m.runs):
                lines.append(
                    f"| {m.config_name} | {model} | n/a (run failed) | n/a | n/a | n/a |"
                )
            else:
                lines.append(
                    f"| {m.config_name} | {model} | {m.success_rate.mean:.1f}% | "
                    f"{m.avg_steps.mean:.1f} | {m.avg_elapsed_ms.mean:.0f} | {total_tokens} |"
                )
        return lines

    @staticmethod
    def _task_passed_flags(metrics: EvalMetrics) -> list[bool]:
        return [r.success and r.expected_check for r in metrics.results]

    def _bootstrap_single_run_section(self, a: EvalMetrics, b: EvalMetrics) -> list[str]:
        lines = ["\n## Bootstrap 95% CI (per-task resampling)\n"]
        ci_a = bootstrap_proportion_ci(a.passed, a.total_tasks)
        ci_b = bootstrap_proportion_ci(b.passed, b.total_tasks)
        if ci_a:
            lines.append(f"- {a.config_name} success rate: {ci_a.format_pct()}")
        if ci_b:
            lines.append(f"- {b.config_name} success rate: {ci_b.format_pct()}")
        passed_a = self._task_passed_flags(a)
        passed_b = self._task_passed_flags(b)
        if len(passed_a) == len(passed_b) and passed_a:
            delta_ci = bootstrap_paired_success_rate_delta_ci(passed_a, passed_b)
            if delta_ci:
                lines.append(
                    f"- Delta ({b.config_name} - {a.config_name}): {delta_ci.format_delta()} "
                    "(基于首轮配对任务，受单轮方差影响，仅供参考)"
                )
        lines.append(f"- Significance: {significance_conclusion(ci_a, ci_b)}")
        return lines

    def _bootstrap_repeated_run_section(self, a: RepeatedEvalMetrics, b: RepeatedEvalMetrics) -> list[str]:
        lines = ["\n## Bootstrap 95% CI\n"]
        if a.success_rate_ci:
            lines.append(f"- {a.config_name} success rate (run resampling): {a.success_rate_ci.format_pct()}")
        if b.success_rate_ci:
            lines.append(f"- {b.config_name} success rate (run resampling): {b.success_rate_ci.format_pct()}")
        if a.runs and b.runs and a.runs[0].results and b.runs[0].results:
            passed_a = self._task_passed_flags(a.runs[0])
            passed_b = self._task_passed_flags(b.runs[0])
            if len(passed_a) == len(passed_b):
                delta_ci = bootstrap_paired_success_rate_delta_ci(passed_a, passed_b)
                if delta_ci:
                    lines.append(
                        f"- Delta ({b.config_name} - {a.config_name}, first run tasks): "
                        f"{delta_ci.format_delta()} (基于首轮配对任务，受单轮方差影响，仅供参考)"
                    )
        ci_a = a.success_rate_ci
        ci_b = b.success_rate_ci
        lines.append(
            f"- Significance: {significance_conclusion(ci_a, ci_b, valid_run_count_a=a.valid_run_count, valid_run_count_b=b.valid_run_count)}"
        )
        return lines

    def _build_csv(self, metrics_list: list[EvalMetrics] | list[RepeatedEvalMetrics]) -> str:
        buf = StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "config", "run_index", "task_id", "success", "expected_check", "steps",
            "elapsed_ms", "tokens", "tool_failures", "policy_blocks", "failure_reason",
            "expected_failures", "trace_file",
        ])
        for m in metrics_list:
            if isinstance(m, RepeatedEvalMetrics):
                for run_index, run in enumerate(m.runs, start=1):
                    for r in run.results:
                        writer.writerow([
                            m.config_name, run_index, r.task_id, r.success, r.expected_check,
                            r.steps, r.elapsed_ms, r.tokens, r.tool_failures,
                            r.policy_blocks, r.failure_reason.value,
                            "; ".join(r.expected_failures), r.trace_file,
                        ])
            else:
                for r in m.results:
                    writer.writerow([
                        m.config_name, 1, r.task_id, r.success, r.expected_check,
                        r.steps, r.elapsed_ms, r.tokens, r.tool_failures,
                        r.policy_blocks, r.failure_reason.value,
                        "; ".join(r.expected_failures), r.trace_file,
                    ])
        return buf.getvalue()
