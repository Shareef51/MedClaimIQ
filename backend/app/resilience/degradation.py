from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum


class Dependency(StrEnum):
    OPENAI = "openai"
    REDIS = "redis"
    QDRANT = "qdrant"
    KAFKA = "kafka"
    POSTGRESQL = "postgresql"
    MCP_EXTERNAL = "external-mcp-tool"


@dataclass(frozen=True)
class DegradationPlan:
    dependency: Dependency
    fallback: str
    retryable: bool
    preserves_authorization: bool = True
    allows_partial_write: bool = False


PLANS = {
    Dependency.OPENAI: DegradationPlan(Dependency.OPENAI, "bounded-retry-then-human-review", True),
    Dependency.REDIS: DegradationPlan(Dependency.REDIS, "degraded-cacheless-operation-where-safe", True),
    Dependency.QDRANT: DegradationPlan(Dependency.QDRANT, "structured-authoritative-evidence-or-human-review", True),
    Dependency.KAFKA: DegradationPlan(Dependency.KAFKA, "transactional-outbox-retains-events", True),
    Dependency.POSTGRESQL: DegradationPlan(Dependency.POSTGRESQL, "fail-request-no-unsafe-partial-write", True),
    Dependency.MCP_EXTERNAL: DegradationPlan(Dependency.MCP_EXTERNAL, "circuit-open-fast-fail", True),
}


def plan_for(dependency: str | Dependency) -> DegradationPlan:
    return PLANS[Dependency(dependency)]
