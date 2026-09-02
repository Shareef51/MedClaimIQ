from __future__ import annotations
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class RegulatoryRemediationLessonModel(Base):
    __tablename__ = "regulatory_remediation_lessons"
    __table_args__ = (UniqueConstraint("tenant_id", "lesson_key", "version", name="uq_reg_lesson_version"),)
    lesson_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    lesson_key: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    source_outcome_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    source_reclosure_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    root_cause_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    control_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    successful_pattern_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    failed_pattern_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    affected_entities: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    effectiveness_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    recurrence_risk_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    lesson_summary: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="candidate")
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RegulatoryFeedbackObservationModel(Base):
    __tablename__ = "regulatory_feedback_observations"
    feedback_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    regulator_ref: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    examination_ref: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    correspondence_ref: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    feedback_type: Mapped[str] = mapped_column(String(80), nullable=False)
    documented_position: Mapped[str] = mapped_column(Text, nullable=False)
    enterprise_interpretation: Mapped[str] = mapped_column(Text, nullable=False)
    ai_observation: Mapped[str | None] = mapped_column(Text, nullable=True)
    supervisory_themes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    evidence_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ControlImprovementProposalModel(Base):
    __tablename__ = "control_improvement_proposals"
    proposal_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    lesson_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    proposal_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    expected_benefit: Mapped[str] = mapped_column(Text, nullable=False)
    risk_if_not_adopted: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    cross_entity_scope: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="proposed")
    human_approval_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    proposed_by_user_id: Mapped[str] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False)
    proposed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ControlImprovementDecisionModel(Base):
    __tablename__ = "control_improvement_decisions"
    decision_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    proposal_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    approval_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    decided_by_user_id: Mapped[str] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class KnowledgePromotionModel(Base):
    __tablename__ = "regulatory_knowledge_promotions"
    promotion_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    lesson_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    knowledge_target: Mapped[str] = mapped_column(String(120), nullable=False)
    source_hashes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    approved_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending_human_approval")
    promoted_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=True)
    promoted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
