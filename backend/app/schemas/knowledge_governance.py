from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


class SourceOnboardRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_key: str = Field(min_length=3, max_length=180)
    source_type: str = Field(min_length=2, max_length=80)
    display_name: str = Field(min_length=2, max_length=200)
    owner_principal_id: str = Field(min_length=3, max_length=128)
    owner_team: str | None = Field(default=None, max_length=128)
    authority_rank: int = Field(ge=0, le=100)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: str
    document_key: str = Field(min_length=2, max_length=220)
    title: str = Field(min_length=2, max_length=300)
    domain: Literal["claim", "policy", "hospital", "invoice", "coding", "historical_claims", "evidence"]
    source_locator: str | None = Field(default=None, max_length=1000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class VersionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: str = Field(min_length=1, max_length=100)
    content_sha256: str = Field(pattern=r"^[a-fA-F0-9]{64}$")
    content_locator: str | None = Field(default=None, max_length=1000)
    rag_source_id: str = Field(min_length=1, max_length=256)
    rag_source_version: str = Field(min_length=1, max_length=128)
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class QualityRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    citation_coverage: float = Field(ge=0, le=1)


class ApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(min_length=3, max_length=1000)


class ProjectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["incremental", "full", "delete", "migrate"]
    embedding_model: str = Field(min_length=2, max_length=160)
    embedding_dimensions: int = Field(gt=0, le=100000)
    index_version: str = Field(min_length=1, max_length=100)


class IndexMigrationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    from_embedding_model: str
    from_dimensions: int = Field(gt=0)
    from_index_version: str
    to_embedding_model: str
    to_dimensions: int = Field(gt=0)
    to_index_version: str


class DriftEvaluationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    release_id: str | None = None
    baseline_metrics: dict[str, float]
    observed_metrics: dict[str, float]


class ReleaseCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    release_key: str = Field(min_length=3, max_length=180)
    release_version: str = Field(min_length=1, max_length=100)
    version_ids: list[str] = Field(min_length=1, max_length=500)


class ReleasePromoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(min_length=3, max_length=1000)
    embedding_model: str
    embedding_dimensions: int = Field(gt=0)
    index_version: str


class StaleScanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    embedding_model: str
    embedding_dimensions: int = Field(gt=0)
    index_version: str
