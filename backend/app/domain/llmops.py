from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Mapping


class AIOperationKind(StrEnum):
    MODEL = "model"
    EMBEDDING = "embedding"
    RETRIEVAL = "retrieval"
    AGENT = "agent"
    TOOL = "tool"
    EVALUATION = "evaluation"
    EVENT = "event"


class SLOKind(StrEnum):
    MODEL_LATENCY_P95 = "model_latency_p95_ms"
    RETRIEVAL_LATENCY_P95 = "retrieval_latency_p95_ms"
    AGENT_ERROR_RATE = "agent_error_rate"
    MCP_ERROR_RATE = "mcp_error_rate"
    DAILY_COST_USD = "daily_cost_usd"


@dataclass(frozen=True, slots=True)
class ModelPricing:
    model: str
    input_usd_per_million: float | None = None
    output_usd_per_million: float | None = None
    version: str = "unconfigured"

    def estimate(self, input_tokens: int | None, output_tokens: int | None) -> float | None:
        if self.input_usd_per_million is None or self.output_usd_per_million is None:
            return None
        return round(
            ((input_tokens or 0) / 1_000_000) * self.input_usd_per_million
            + ((output_tokens or 0) / 1_000_000) * self.output_usd_per_million,
            8,
        )


@dataclass(frozen=True, slots=True)
class SLOThresholds:
    model_latency_p95_ms: float = 15_000
    retrieval_latency_p95_ms: float = 2_000
    agent_error_rate: float = 0.05
    mcp_error_rate: float = 0.02
    daily_cost_usd: float = 100.0

    @classmethod
    def from_mapping(cls, raw: Mapping[str, object]) -> "SLOThresholds":
        return cls(**{key: float(value) for key, value in raw.items() if hasattr(cls, key)})
