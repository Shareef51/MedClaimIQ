from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field

class SustainabilityObservationRequest(BaseModel):
    intervention_program_id:str; reclosure_version_id:str; baseline_control_health:float=100; current_control_health:float=100; minimum_control_health:float=80; material_decay_threshold:float=15; evidence_refs:list[str]=Field(default_factory=list)
class MultiCycleRecurrenceRequest(BaseModel): intervention_program_id:str; cycles:list[dict[str,Any]]=Field(default_factory=list)
class PriorReclosureComparisonRequest(BaseModel): intervention_program_id:str; prior:dict[str,Any]; current:dict[str,Any]
class CrossEntityPropagationRequest(BaseModel): intervention_program_id:str; observed_entity_ids:list[str]=Field(default_factory=list); in_scope_entity_ids:list[str]=Field(default_factory=list)
class RegulatorFollowUpCorrelationRequest(BaseModel): intervention_program_id:str; follow_ups:list[dict[str,Any]]=Field(default_factory=list)
class EnterpriseMaterialityRequest(BaseModel): intervention_program_id:str; multi_cycle_recurrence_score:float=0; propagation_ratio:float=0; systemic_risk_rebound:float=0; regulatory_follow_up_risk:bool=False
class SupervisoryEscalationCreate(BaseModel): intervention_program_id:str; escalation_tier:str; rationale:str; recurrence_evidence_refs:list[str]=Field(default_factory=list); executive_review_required:bool=True; internal_audit_review_required:bool=True
class SupervisoryInvestigationCreate(BaseModel): intervention_program_id:str; escalation_version_id:str; investigator_role:str; hypothesis:str; evidence_refs:list[str]=Field(default_factory=list)
class HumanChallengeRequest(BaseModel): intervention_program_id:str; reviewer_role:str; decision:str; rationale:str; evidence_refs:list[str]=Field(default_factory=list)
class GovernanceActionRequest(BaseModel): intervention_program_id:str; actor_role:str; action_type:str; decision:str; rationale:str; evidence_refs:list[str]=Field(default_factory=list)
