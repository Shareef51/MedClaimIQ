from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field
class RecoveryDecayRequest(BaseModel):
    intervention_program_id:str; baseline_control_health_score:float=100; current_control_health_score:float=100; failed_observation_count:int=0; stale_evidence_count:int=0; sustainability_breach_count:int=0; days_since_reclosure:int=0
class MultiCycleRecurrenceRequest(BaseModel):
    intervention_program_id:str; cycles:list[dict[str,Any]]=Field(default_factory=list)
class RiskReboundRequest(BaseModel):
    intervention_program_id:str; reclosure_risk_score:float=0; risk_history:list[dict[str,Any]]=Field(default_factory=list)
class ReclosureComparisonRequest(BaseModel):
    intervention_program_id:str; prior:dict[str,Any]=Field(default_factory=dict); current:dict[str,Any]=Field(default_factory=dict)
class RegulatorFollowupCorrelationRequest(BaseModel):
    intervention_program_id:str; followups:list[dict[str,Any]]=Field(default_factory=list)
class EnterpriseMaterialityRequest(BaseModel):
    intervention_program_id:str; failed_cycle_count:int=0; affected_entity_count:int=0; recovery_decay_score:float=0; peak_rebound:float=0; regulator_attention_escalation:bool=False; critical_service_impact:bool=False
class SupervisoryInvestigationRequest(BaseModel):
    intervention_program_id:str; actor_role:str; recurrence_evidence_refs:list[str]=Field(default_factory=list); materiality_score:float; rationale:str
class SupervisoryEscalationRequest(BaseModel):
    intervention_program_id:str; actor_role:str; investigation_version_id:str; escalation_tier:int; decision:str; rationale:str; evidence_refs:list[str]=Field(default_factory=list)
