from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Any
class EffectivenessRetestCreate(BaseModel):
    commitment_id:str; validator_user_id:str; validator_role:str; result:str; rationale:str; evidence_refs:list[str]=Field(default_factory=list); scope_entities:list[str]=Field(default_factory=list)
class ClosureAssessmentRequest(BaseModel):
    commitment:dict[str,Any]=Field(default_factory=dict); milestones:list[dict[str,Any]]=Field(default_factory=list); evidence:list[dict[str,Any]]=Field(default_factory=list); validations:list[dict[str,Any]]=Field(default_factory=list); dependencies:list[dict[str,Any]]=Field(default_factory=list); follow_ups:list[dict[str,Any]]=Field(default_factory=list); entity_checks:list[dict[str,Any]]=Field(default_factory=list)
class ClosureCertificationRequest(ClosureAssessmentRequest):
    reviewer_role:str; decision:str; rationale:str
class SustainabilityObservationCreate(BaseModel):
    commitment_id:str; days_since_closure:int=0; health_score:float=100; control_effective:bool=True; recurrence_detected:bool=False; evidence_refs:list[str]=Field(default_factory=list)
class SustainabilityEvaluationRequest(BaseModel): observations:list[dict[str,Any]]=Field(default_factory=list); min_window_days:int=30
class RecurrenceDetectionRequest(BaseModel): commitment:dict[str,Any]; signals:list[dict[str,Any]]=Field(default_factory=list)
class ReopenDecisionRequest(BaseModel): reviewer_role:str; decision:str; rationale:str; evidence_refs:list[str]=Field(default_factory=list)
