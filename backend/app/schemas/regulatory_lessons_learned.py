from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class LessonCreateRequest(BaseModel):
    lesson_key: str = Field(min_length=3, max_length=180)
    source_outcome_refs: list[dict[str, Any]] = Field(min_length=1)
    source_reclosure_refs: list[dict[str, Any]] = Field(default_factory=list)
    root_cause_refs: list[dict[str, Any]] = Field(default_factory=list)
    control_refs: list[dict[str, Any]] = Field(min_length=1)
    successful_pattern_refs: list[dict[str, Any]] = Field(default_factory=list)
    failed_pattern_refs: list[dict[str, Any]] = Field(default_factory=list)
    affected_entities: list[str] = Field(default_factory=list)
    effectiveness_score: float = Field(ge=0, le=1)
    recurrence_risk_score: float = Field(ge=0, le=1)
    lesson_summary: str = Field(min_length=40)
    evidence_refs: list[dict[str, Any]] = Field(min_length=1)


class RegulatoryFeedbackRequest(BaseModel):
    regulator_ref: dict[str, Any]
    examination_ref: dict[str, Any]
    correspondence_ref: dict[str, Any]
    feedback_type: str
    documented_position: str = Field(min_length=20)
    enterprise_interpretation: str = Field(min_length=20)
    ai_observation: str | None = None
    supervisory_themes: list[str] = Field(default_factory=list)
    evidence_refs: list[dict[str, Any]] = Field(min_length=1)
    effective_at: datetime


class ControlImprovementProposalRequest(BaseModel):
    lesson_id: str
    proposal_type: str = Field(pattern="^(control_redesign|policy_change|procedure_change|monitoring_change|training_change|data_quality_change|technology_change)$")
    target_refs: list[dict[str, Any]] = Field(min_length=1)
    rationale: str = Field(min_length=30)
    expected_benefit: str = Field(min_length=20)
    risk_if_not_adopted: str = Field(min_length=20)
    evidence_refs: list[dict[str, Any]] = Field(min_length=1)
    cross_entity_scope: list[str] = Field(default_factory=list)


class HumanImprovementDecisionRequest(BaseModel):
    decision: str = Field(pattern="^(approve|reject|return_for_revision)$")
    rationale: str = Field(min_length=30)
    approval_refs: list[dict[str, Any]] = Field(default_factory=list)


class KnowledgePromotionRequest(BaseModel):
    lesson_id: str
    knowledge_target: str
    source_hashes: list[str] = Field(min_length=1)
    approved_refs: list[dict[str, Any]] = Field(min_length=1)
