from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from typing import Any


class AIConfigurationType(StrEnum):
    MODEL = "model"
    PROMPT = "prompt"
    RETRIEVAL = "retrieval"
    BUNDLE = "bundle"


class AIEnvironment(StrEnum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class PromotionRisk(StrEnum):
    STANDARD = "standard"
    HIGH = "high"


class PromotionStatus(StrEnum):
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    ACTIVATED = "activated"
    ROLLED_BACK = "rolled_back"


class ExperimentMode(StrEnum):
    SHADOW = "shadow"
    AB = "ab"
    CHAMPION_CHALLENGER = "champion_challenger"


class ExperimentStatus(StrEnum):
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


SECRET_KEY_FRAGMENTS = ("secret", "password", "token", "api_key", "apikey", "authorization", "cookie")


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_json(value: Any) -> str:
    return sha256(canonical_json(value).encode()).hexdigest()


def validate_configuration_payload(payload: dict[str, Any]) -> None:
    """Reject secret-bearing configuration. Runtime credentials belong in KMS/secret stores."""
    stack: list[tuple[str, Any]] = [("$", payload)]
    while stack:
        path, value = stack.pop()
        if isinstance(value, dict):
            for key, child in value.items():
                normalized = str(key).lower().replace("-", "_")
                if any(fragment in normalized for fragment in SECRET_KEY_FRAGMENTS):
                    raise ValueError(f"secret-like configuration key is prohibited: {path}.{key}")
                stack.append((f"{path}.{key}", child))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                stack.append((f"{path}[{index}]", child))


@dataclass(frozen=True, slots=True)
class CohortAssignment:
    bucket: int
    variant: str


def deterministic_cohort(*, tenant_id: str, experiment_id: str, subject_key: str, challenger_basis_points: int) -> CohortAssignment:
    if not 0 <= challenger_basis_points <= 10_000:
        raise ValueError("challenger_basis_points must be between 0 and 10000")
    digest = sha256(f"{tenant_id}|{experiment_id}|{subject_key}".encode()).hexdigest()
    bucket = int(digest[:8], 16) % 10_000
    return CohortAssignment(bucket=bucket, variant="challenger" if bucket < challenger_basis_points else "champion")


def classify_promotion_risk(*, environment: str, configuration_type: str) -> PromotionRisk:
    # Every production model/prompt/retrieval change is high-risk because it can alter claim-support output.
    if environment == AIEnvironment.PRODUCTION.value:
        return PromotionRisk.HIGH
    if configuration_type in {AIConfigurationType.MODEL.value, AIConfigurationType.PROMPT.value, AIConfigurationType.BUNDLE.value}:
        return PromotionRisk.HIGH
    return PromotionRisk.STANDARD


def compare_experiment_metrics(*, champion: dict[str, float], challenger: dict[str, float], guardrails: dict[str, float]) -> dict[str, Any]:
    """Compare quality/cost/latency without allowing cheaper/faster output to hide quality regression."""
    quality_floor = float(guardrails.get("quality_floor", 0.0))
    max_quality_regression = float(guardrails.get("max_quality_regression", 0.0))
    max_latency_regression = float(guardrails.get("max_latency_regression_fraction", 1.0))
    max_cost_regression = float(guardrails.get("max_cost_regression_fraction", 1.0))
    cq = float(champion.get("quality", 0.0)); nq = float(challenger.get("quality", 0.0))
    cl = max(float(champion.get("latency_ms", 0.0)), 1e-9); nl = float(challenger.get("latency_ms", 0.0))
    cc = max(float(champion.get("cost_usd", 0.0)), 1e-9); nc = float(challenger.get("cost_usd", 0.0))
    reasons: list[str] = []
    if nq < quality_floor:
        reasons.append("challenger_quality_below_floor")
    if cq - nq > max_quality_regression:
        reasons.append("challenger_quality_regression_exceeded")
    if (nl - cl) / cl > max_latency_regression:
        reasons.append("challenger_latency_regression_exceeded")
    if (nc - cc) / cc > max_cost_regression:
        reasons.append("challenger_cost_regression_exceeded")
    return {
        "decision": "pass" if not reasons else "block",
        "reasons": reasons,
        "deltas": {"quality": nq - cq, "latency_ms": nl - cl, "cost_usd": nc - cc},
    }
