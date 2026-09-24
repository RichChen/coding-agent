"""Private evaluator DTOs. Never import these into a strategy input."""

from typing import Literal

from reposkill_agent.protocol.public import ProtocolMode, Versioned


class EvaluationSpec(Versioned):
    task_id: str
    expected_files: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    gold_patch: str | None = None
    hidden_test_refs: tuple[str, ...] = ()
    future_trajectory_refs: tuple[str, ...] = ()


class EvaluationResult(Versioned):
    task_id: str
    protocol_mode: ProtocolMode
    outcome: Literal["pass", "fail", "partial", "invalid_env"]
    evidence_refs: tuple[str, ...] = ()
    collected: int = 0
    passed: int = 0


def aggregate_results(results: list[EvaluationResult]) -> dict:
    if len({r.protocol_mode for r in results}) > 1:
        raise ValueError("mixed_protocol_modes")
    count = len(results)
    passed = sum(r.outcome == "pass" for r in results)
    if any(r.outcome == "pass" and (r.collected <= 0 or r.passed != r.collected) for r in results):
        raise ValueError("unverified_pass")
    return {
        "assigned": count,
        "pass": passed,
        "success_rate": passed / count if count else None,
        "invalid_env": sum(r.outcome == "invalid_env" for r in results),
        "protocol_mode": results[0].protocol_mode if results else None,
    }
