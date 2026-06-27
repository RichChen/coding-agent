"""Bootstrap confidence intervals for eval metrics."""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class ConfidenceInterval:
    low: float
    high: float
    level: float = 0.95

    def format_pct(self) -> str:
        return f"[{self.low:.1f}%, {self.high:.1f}%]"

    def format_delta(self) -> str:
        return f"[{self.low:+.1f}%, {self.high:+.1f}%]"


def bootstrap_proportion_ci(
    successes: int,
    total: int,
    *,
    n_bootstrap: int = 2000,
    confidence: float = 0.95,
    seed: int = 0,
) -> ConfidenceInterval | None:
    if total <= 0:
        return None
    rng = random.Random(seed)
    alpha = 1.0 - confidence
    samples: list[float] = []
    for _ in range(n_bootstrap):
        hits = sum(rng.random() < (successes / total) for _ in range(total))
        samples.append(hits / total * 100.0)
    samples.sort()
    low_idx = int((alpha / 2) * n_bootstrap)
    high_idx = int((1 - alpha / 2) * n_bootstrap) - 1
    return ConfidenceInterval(
        low=samples[low_idx],
        high=samples[high_idx],
        level=confidence,
    )


def bootstrap_mean_ci(
    values: list[float],
    *,
    n_bootstrap: int = 2000,
    confidence: float = 0.95,
    seed: int = 0,
) -> ConfidenceInterval | None:
    if not values:
        return None
    rng = random.Random(seed)
    alpha = 1.0 - confidence
    samples: list[float] = []
    n = len(values)
    for _ in range(n_bootstrap):
        draw = [values[rng.randrange(n)] for _ in range(n)]
        samples.append(sum(draw) / len(draw))
    samples.sort()
    low_idx = int((alpha / 2) * n_bootstrap)
    high_idx = int((1 - alpha / 2) * n_bootstrap) - 1
    return ConfidenceInterval(low=samples[low_idx], high=samples[high_idx], level=confidence)


def bootstrap_paired_success_rate_delta_ci(
    passed_a: list[bool],
    passed_b: list[bool],
    *,
    n_bootstrap: int = 2000,
    confidence: float = 0.95,
    seed: int = 0,
) -> ConfidenceInterval | None:
    if not passed_a or len(passed_a) != len(passed_b):
        return None
    rng = random.Random(seed)
    alpha = 1.0 - confidence
    n = len(passed_a)
    deltas: list[float] = []
    for _ in range(n_bootstrap):
        idxs = [rng.randrange(n) for _ in range(n)]
        rate_a = sum(passed_a[i] for i in idxs) / n * 100.0
        rate_b = sum(passed_b[i] for i in idxs) / n * 100.0
        deltas.append(rate_b - rate_a)
    deltas.sort()
    low_idx = int((alpha / 2) * n_bootstrap)
    high_idx = int((1 - alpha / 2) * n_bootstrap) - 1
    return ConfidenceInterval(
        low=deltas[low_idx],
        high=deltas[high_idx],
        level=confidence,
    )
