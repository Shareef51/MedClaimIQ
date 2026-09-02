from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class CanonicalEntityModel(TimestampMixin, Base):
    __tablename__ = "canonical_entities"
    __table_args__ = (
        UniqueConstraint("tenant_id", "entity_type", "canonical_key", name="canonical_key_per_tenant_type"),
        Index("ix_canonical_entity_tenant_claim", "tenant_id", "claim_id", "entity_type"),
        Index("ix_canonical_entity_tenant_patient", "tenant_id", "patient_subject_id", "entity_type"),
    )
    entity_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(60), nullable=False)
    canonical_key: Mapped[str] = mapped_column(String(512), nullable=False)
    claim_id: Mapped[str | None] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=True, index=True)
    patient_subject_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    attributes: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")


class SourceEntityMappingModel(Base):
    __tablename__ = "source_entity_mappings"
    __table_args__ = (
        UniqueConstraint("tenant_id", "source_type", "source_system", "resource_type", "resource_id", "source_version", name="source_identity_per_version"),
        Index("ix_source_mapping_entity", "tenant_id", "entity_id"),
        Index("ix_source_mapping_claim", "tenant_id", "claim_id"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence_range"),
        CheckConstraint("authority_rank >= 0 AND authority_rank <= 100", name="authority_range"),
    )
    mapping_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(ForeignKey("canonical_entities.entity_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str | None] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=True, index=True)
    source_type: Mapped[str] = mapped_column(String(60), nullable=False)
    source_system: Mapped[str] = mapped_column(String(160), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(256), nullable=False)
    source_version: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    content_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_locator: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    authority_rank: Mapped[int] = mapped_column(nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(6, 5), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)


class CanonicalCodeMappingModel(TimestampMixin, Base):
    __tablename__ = "canonical_code_mappings"
    __table_args__ = (
        UniqueConstraint("tenant_id", "source_system", "source_code", name="source_code_per_tenant"),
        Index("ix_code_mapping_canonical", "tenant_id", "canonical_system", "canonical_code"),
    )
    code_mapping_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    source_system: Mapped[str] = mapped_column(String(200), nullable=False)
    source_code: Mapped[str] = mapped_column(String(100), nullable=False)
    canonical_system: Mapped[str] = mapped_column(String(80), nullable=False)
    canonical_code: Mapped[str] = mapped_column(String(100), nullable=False)
    display: Mapped[str | None] = mapped_column(String(500), nullable=True)
    mapping_method: Mapped[str] = mapped_column(String(40), nullable=False, default="deterministic_alias")
    mapping_version: Mapped[str] = mapped_column(String(80), nullable=False, default="v1")


class ClaimLineCrosswalkModel(TimestampMixin, Base):
    __tablename__ = "claim_line_crosswalks"
    __table_args__ = (
        UniqueConstraint("tenant_id", "claim_line_id", "source_mapping_id", name="crosswalk_candidate_once"),
        Index("ix_crosswalk_claim", "tenant_id", "claim_id", "status"),
        CheckConstraint("score >= 0 AND score <= 1", name="score_range"),
    )
    crosswalk_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_line_id: Mapped[str] = mapped_column(ForeignKey("claim_lines.claim_line_id", ondelete="CASCADE"), nullable=False, index=True)
    source_mapping_id: Mapped[str] = mapped_column(ForeignKey("source_entity_mappings.mapping_id", ondelete="CASCADE"), nullable=False, index=True)
    score: Mapped[Decimal] = mapped_column(Numeric(6, 5), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    service_date_alignment: Mapped[str] = mapped_column(String(30), nullable=False, default="unknown")


class EvidenceGraphEdgeModel(Base):
    __tablename__ = "evidence_graph_edges"
    __table_args__ = (
        UniqueConstraint("tenant_id", "edge_fingerprint", name="edge_once_per_tenant"),
        Index("ix_graph_edge_source", "tenant_id", "source_entity_id", "relationship_type"),
        Index("ix_graph_edge_target", "tenant_id", "target_entity_id", "relationship_type"),
        Index("ix_graph_edge_claim", "tenant_id", "claim_id"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence_range"),
        CheckConstraint("authority_rank >= 0 AND authority_rank <= 100", name="authority_range"),
    )
    edge_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str | None] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=True, index=True)
    source_entity_id: Mapped[str] = mapped_column(ForeignKey("canonical_entities.entity_id", ondelete="CASCADE"), nullable=False, index=True)
    target_entity_id: Mapped[str] = mapped_column(ForeignKey("canonical_entities.entity_id", ondelete="CASCADE"), nullable=False, index=True)
    relationship_type: Mapped[str] = mapped_column(String(60), nullable=False)
    edge_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(6, 5), nullable=False)
    authority_rank: Mapped[int] = mapped_column(nullable=False)
    provenance_refs: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    attributes: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EvidenceContradictionModel(TimestampMixin, Base):
    __tablename__ = "evidence_contradictions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "contradiction_fingerprint", name="contradiction_once_per_tenant"),
        Index("ix_contradiction_claim", "tenant_id", "claim_id", "status", "severity"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence_range"),
    )
    contradiction_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    subject_entity_id: Mapped[str | None] = mapped_column(ForeignKey("canonical_entities.entity_id", ondelete="SET NULL"), nullable=True, index=True)
    field_name: Mapped[str] = mapped_column(String(120), nullable=False)
    left_mapping_id: Mapped[str] = mapped_column(ForeignKey("source_entity_mappings.mapping_id", ondelete="RESTRICT"), nullable=False)
    right_mapping_id: Mapped[str] = mapped_column(ForeignKey("source_entity_mappings.mapping_id", ondelete="RESTRICT"), nullable=False)
    left_value: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    right_value: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    severity: Mapped[str] = mapped_column(String(30), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(6, 5), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="open")
    contradiction_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="SET NULL"), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RAGMetadataRecordModel(TimestampMixin, Base):
    __tablename__ = "rag_metadata_records"
    __table_args__ = (
        UniqueConstraint("tenant_id", "source_type", "source_id", "source_version", name="rag_source_version_once"),
        Index("ix_rag_metadata_claim", "tenant_id", "claim_id"),
        Index("ix_rag_metadata_patient", "tenant_id", "patient_subject_id"),
    )
    metadata_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    patient_subject_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(60), nullable=False)
    source_id: Mapped[str] = mapped_column(String(256), nullable=False)
    source_version: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    entity_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    relationship_types: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    rag_metadata: Mapped[dict[str, object]] = mapped_column("metadata", JSON, nullable=False, default=dict)
    evidence_confidence: Mapped[Decimal] = mapped_column(Numeric(6, 5), nullable=False)
    authority_rank: Mapped[int] = mapped_column(nullable=False)
