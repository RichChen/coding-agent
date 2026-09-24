"""Report formatting for ablation outputs."""

from __future__ import annotations

from pathlib import Path


def write_ablation_markdown(summary: dict, output_path: Path) -> None:
    """Write markdown summary table for ablation results."""
    lines = [
        "# Phase 6 Ablation Summary",
        "",
        "Protocol: `diagnostic_oracle` (legacy; not realistic repair evaluation)",
        "",
        f"Run ID: `{summary['run_id']}`",
        f"Generated at: `{summary['generated_at']}`",
        f"Task count: `{summary['task_count']}`",
        f"Repeats: `{summary['repeats']}`",
        f"Seed: `{summary.get('seed', 42)}`",
        f"Seed memory: `{summary.get('seed_memory', False)}`",
        f"Hard mode: `{summary.get('hard_mode', False)}`",
        "",
        "| Config | success_rate+/-std | avg_steps+/-std | avg_replan+/-std |"
        " skill_neg_transfer | memory_useful | memory_stale | role_handoff | roles_used |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for config_name, data in summary["results"].items():
        agg = data["aggregate"]
        var = data.get("variance", {})
        success = f"{agg['success_rate']:.2f}+/-{var.get('success_rate_std', 0.0):.2f}"
        steps = f"{agg['avg_steps']:.2f}+/-{var.get('avg_steps_std', 0.0):.2f}"
        replan = f"{agg['avg_replan_count']:.2f}+/-{var.get('avg_replan_count_std', 0.0):.2f}"
        lines.append(
            "| "
            + f"{config_name} | "
            + f"{success} | "
            + f"{steps} | "
            + f"{replan} | "
            + f"{agg['skill_negative_transfer_total']} | "
            + f"{agg['memory_useful_total']} | "
            + f"{agg['memory_stale_or_wrong_total']} | "
            + f"{agg['avg_role_handoff_count']:.2f} | "
            + f"`{agg['agent_roles_union']}` |"
        )
        dist = agg.get("failure_taxonomy_distribution", {})
        lines.append(f"| {config_name} failure taxonomy | `{dist}` |  |  |  |  |  |  |  |")

    lines.extend(
        [
            "",
            "## By Task Category",
            "",
            "| Config | Category | Tasks | Success Rate | Avg Steps | Avg Replan | Main Failure |",
            "| --- | --- | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for config_name, data in summary["results"].items():
        grouped = data["aggregate"].get("by_category", {})
        for category, values in grouped.items():
            lines.append(
                "| "
                + f"{config_name} | {category} | {values['tasks']} | "
                + f"{values['success_rate']:.2f} | {values['avg_steps']:.2f} | "
                + f"{values['avg_replan_count']:.2f} | {values['main_failure']} |"
            )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_llm_ablation_markdown(summary: dict, output_path: Path) -> None:
    """Write markdown summary for LLM ablation runs (no full prompts)."""
    lines = [
        "# LLM Mechanism Ablation Summary",
        "",
        "Protocol: `diagnostic_oracle` (legacy; not realistic repair evaluation)",
        "Memory useful/stale counts are outcome proxies, not validity or adoption evidence.",
        "",
        f"Run ID: `{summary['run_id']}`",
        f"Generated at: `{summary['generated_at']}`",
        f"Task count: `{summary['task_count']}`",
        f"Repeats: `{summary['repeats']}`",
        f"Seed: `{summary.get('seed', 42)}`",
        f"Mock LLM: `{summary.get('mock_llm', False)}`",
        "",
        "| Config | success_rate+/-std | avg_steps+/-std | llm_calls | parse_err | patch_applied |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for config_name, data in summary["results"].items():
        agg = data["aggregate"]
        var = data.get("variance", {})
        success = f"{agg['success_rate']:.2f}+/-{var.get('success_rate_std', 0.0):.2f}"
        steps = f"{agg['avg_steps']:.2f}+/-{var.get('avg_steps_std', 0.0):.2f}"
        lines.append(
            "| "
            + f"{config_name} | {success} | {steps} | "
            + f"{agg.get('llm_call_total', 0)} | "
            + f"{agg.get('llm_parse_error_total', 0)} | "
            + f"{agg.get('llm_patch_applied_total', 0)} |"
        )
        dist = agg.get("failure_taxonomy_distribution", {})
        lines.append(f"| {config_name} failure taxonomy | `{dist}` |  |  |  |  |")

    lines.extend(
        [
            "",
            "## Skill / Memory Injection",
            "",
            "| Config | skill_cand | skill_inj | skill_gated | mem_cand | mem_inj |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for config_name, data in summary["results"].items():
        agg = data["aggregate"]
        lines.append(
            "| "
            + f"{config_name} | "
            + f"{agg.get('skill_candidate_total', 0)} | "
            + f"{agg.get('skill_injected_total', 0)} | "
            + f"{agg.get('skill_gated_total', 0)} | "
            + f"{agg.get('memory_candidate_total', 0)} | "
            + f"{agg.get('memory_injected_total', 0)} |"
        )

    lines.extend(
        [
            "",
            "## Augmentation Policy Suppression",
            "",
            "| Config | skill_suppressed | mem_suppressed |",
            "| --- | ---: | ---: |",
        ]
    )
    for config_name, data in summary["results"].items():
        agg = data["aggregate"]
        lines.append(
            "| "
            + f"{config_name} | "
            + f"{agg.get('skill_suppressed_by_policy_total', 0)} | "
            + f"{agg.get('memory_suppressed_by_policy_total', 0)} |"
        )

    lines.extend(
        [
            "",
            "## Context Expansion / JSON Repair",
            "",
            "| Config | ctx_expand | paths_added | ctx_recovered | repair_try | repair_ok |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for config_name, data in summary["results"].items():
        agg = data["aggregate"]
        lines.append(
            "| "
            + f"{config_name} | "
            + f"{agg.get('context_expansion_total', 0)} | "
            + f"{agg.get('allowed_path_added_total', 0)} | "
            + f"{agg.get('needs_more_context_recovered_total', 0)} | "
            + f"{agg.get('llm_parse_repair_attempt_total', 0)} | "
            + f"{agg.get('llm_parse_repair_success_total', 0)} |"
        )

    lines.extend(
        [
            "",
            "## By Task Category",
            "",
            "| Config | Category | Tasks | Success Rate | Avg Steps | Main Failure |",
            "| --- | --- | ---: | ---: | ---: | --- |",
        ]
    )
    for config_name, data in summary["results"].items():
        grouped = data["aggregate"].get("by_category", {})
        for category, values in grouped.items():
            lines.append(
                "| "
                + f"{config_name} | {category} | {values['tasks']} | "
                + f"{values['success_rate']:.2f} | {values['avg_steps']:.2f} | "
                + f"{values['main_failure']} |"
            )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
