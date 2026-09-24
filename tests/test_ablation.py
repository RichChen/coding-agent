"""Tests for Phase 6 ablation runner."""

from pathlib import Path

from reposkill_agent.eval.ablation import AblationRunner
from reposkill_agent.eval.report import write_ablation_markdown
from reposkill_agent.eval.task_spec import load_tasks


def test_ablation_runner_creates_summary(tmp_path: Path):
    catalog = load_tasks(
        Path("benchmarks/tasks/tiny_python_tasks.yaml").resolve(),
        benchmarks_root=Path("benchmarks").resolve(),
    )
    runner = AblationRunner(output_root=tmp_path / "reports", adapter="fake", seed=7)
    summary = runner.run(catalog=catalog, repeats=2)
    assert "results" in summary
    assert "A0_baseline" in summary["results"]
    assert "A5_full" in summary["results"]
    assert summary["seed"] == 7
    assert summary["repeats"] == 2
    json_path = runner.run_dir / "ablation-summary.json"
    assert json_path.exists()
    assert "variance" in summary["results"]["A5_full"]


def test_ablation_markdown_output(tmp_path: Path):
    fake_summary = {
        "run_id": "demo",
        "generated_at": "now",
        "task_count": 3,
        "repeats": 1,
        "seed": 42,
        "seed_memory": False,
        "results": {
            "A0_baseline": {
                "aggregate": {
                    "success_rate": 1.0,
                    "avg_steps": 2.0,
                    "avg_replan_count": 0.0,
                    "skill_negative_transfer_total": 0,
                    "memory_useful_total": 0,
                    "memory_stale_or_wrong_total": 0,
                    "avg_role_handoff_count": 0.0,
                    "agent_roles_union": ["single_agent"],
                    "failure_taxonomy_distribution": {"success": 3},
                },
                "variance": {
                    "success_rate_std": 0.0,
                    "avg_steps_std": 0.0,
                    "avg_wall_time_ms_std": 0.0,
                    "avg_replan_count_std": 0.0,
                }
            }
        },
    }
    out = tmp_path / "ablation.md"
    write_ablation_markdown(fake_summary, out)
    text = out.read_text(encoding="utf-8")
    assert "Phase 6 Ablation Summary" in text
    assert "A0_baseline" in text
