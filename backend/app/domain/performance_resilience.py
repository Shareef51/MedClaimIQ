from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import ceil
from statistics import mean


class GateDecision(StrEnum):
    PASS = "pass"
    BLOCK = "block"


class ExperimentStatus(StrEnum):
    PLANNED = "planned"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ABORTED = "aborted"


@dataclass(frozen=True)
class MetricBudget:
    key: str
    threshold: float
    comparator: str = "lte"

    def passes(self, observed: float) -> bool:
        if self.comparator == "lte":
            return observed <= self.threshold
        if self.comparator == "gte":
            return observed >= self.threshold
        raise ValueError(f"unsupported comparator {self.comparator}")


def percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    if quantile <= 0 or quantile > 1:
        raise ValueError("quantile must be within (0, 1]")
    ordered = sorted(float(v) for v in values)
    return ordered[max(0, ceil(quantile * len(ordered)) - 1)]


def summarize_latencies(values: list[float]) -> dict[str, float]:
    return {
        "count": float(len(values)),
        "mean_ms": round(mean(values), 3) if values else 0.0,
        "p50_ms": round(percentile(values, 0.50), 3),
        "p95_ms": round(percentile(values, 0.95), 3),
        "p99_ms": round(percentile(values, 0.99), 3),
        "max_ms": round(max(values), 3) if values else 0.0,
    }


def regression_fraction(candidate: float, baseline: float) -> float:
    if baseline <= 0:
        return 0.0 if candidate <= baseline else 1.0
    return (candidate - baseline) / baseline
