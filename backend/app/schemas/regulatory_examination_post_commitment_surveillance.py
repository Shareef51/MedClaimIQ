from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Any

class SurveillanceObservationCreate(BaseModel):
    commitment_id:str; days_since_closure:int=0; health_score:float=100.0; control_effective:bool=True; recurrence_detected:bool=False; control_id:str|None=None; entity_id:str|None=None; examination_id:str|None=None; evidence_refs:list[str]=Field(default_factory=list)
class SustainabilityDecayRequest(BaseModel):
    observations:list[dict[str,Any]]=Field(default_factory=list); warning_threshold:float=80.0; critical_threshold:float=60.0
class ExaminationMatchRequest(BaseModel):
    closed_commitment:dict[str,Any]; findings:list[dict[str,Any]]=Field(default_factory=list)
class CrossEntityRecurrenceRequest(BaseModel):
    signals:list[dict[str,Any]]=Field(default_factory=list); minimum_entities:int=2
class CertificationComparisonRequest(BaseModel):
    certification:dict[str,Any]; current_evidence:dict[str,Any]
class RecurrenceInvestigationCreate(BaseModel):
    commitment_id:str; trigger_type:str; rationale:str; evidence_refs:list[str]=Field(default_factory=list); matched_finding_ids:list[str]=Field(default_factory=list); affected_entity_ids:list[str]=Field(default_factory=list)
class RenewedActionPlanLinkRequest(BaseModel):
    investigation_id:str; action_plan_id:str; owner_user_id:str; due_date:str|None=None; evidence_refs:list[str]=Field(default_factory=list)
class IndependentReassessmentCreate(BaseModel):
    investigation_id:str; reviewer_role:str; result:str; rationale:str; evidence_refs:list[str]=Field(default_factory=list)
class ReopenDecisionRequest(BaseModel):
    investigation_id:str; reviewer_role:str; decision:str; rationale:str; evidence_refs:list[str]=Field(default_factory=list)
