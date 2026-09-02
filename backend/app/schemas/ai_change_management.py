from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


class ConfigSnapshotCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    config_key: str = Field(min_length=3, max_length=180)
    version: str = Field(min_length=1, max_length=80)
    configuration_type: Literal["model", "prompt", "retrieval", "bundle"]
    payload: dict[str, Any]
    parent_snapshot_id: str | None = None
    evaluation_baseline_id: str | None = None
    evaluation_run_id: str | None = None


class PromotionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    snapshot_id: str
    target_environment: Literal["development", "staging", "production"]
    evaluation_run_id: str | None = None
    evaluation_decision: Literal["pass", "block"] | None = None


class PromotionDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    approve: bool
    reason: str = Field(min_length=3, max_length=1000)


class RollbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    environment: Literal["development", "staging", "production"]
    config_key: str
    target_snapshot_id: str
    reason: str = Field(min_length=3, max_length=1000)


class ExperimentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    experiment_key: str = Field(min_length=3, max_length=160)
    environment: Literal["development", "staging", "production"]
    mode: Literal["shadow", "ab", "champion_challenger"]
    champion_snapshot_id: str
    challenger_snapshot_id: str
    challenger_basis_points: int = Field(ge=0, le=10000)
    evaluation_baseline_id: str | None = None
    guardrails: dict[str, float] = Field(default_factory=dict)


class ExperimentAssignRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subject_key: str = Field(min_length=1, max_length=256)


class ExperimentObservationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    assignment_id: str | None = None
    variant: Literal["champion", "challenger"]
    quality_score: float | None = Field(default=None, ge=0, le=1)
    latency_ms: float | None = Field(default=None, ge=0)
    cost_usd: float | None = Field(default=None, ge=0)
    evaluation_run_id: str | None = None
    trace_id: str | None = None
    evidence_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class DriftCheckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    environment: Literal["development", "staging", "production"]
    config_key: str
    observed_payload: dict[str, Any]
