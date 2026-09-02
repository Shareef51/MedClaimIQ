from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field

class ReopenedInterventionPlanCreate(BaseModel):
    intervention_program_id:str; reopening_version_id:str; owner_user_id:str; rationale:str
    affected_entity_ids:list[str]=Field(default_factory=list); renewed_commitment_ids:list[str]=Field(default_factory=list); evidence_refs:list[str]=Field(default_factory=list)
class RenewedSystemicActionCreate(BaseModel):
    plan_id:str; title:str; owner_user_id:str; control_ids:list[str]=Field(default_factory=list); entity_ids:list[str]=Field(default_factory=list); due_date:str|None=None; dependency_ids:list[str]=Field(default_factory=list); evidence_refs:list[str]=Field(default_factory=list)
class RootCauseComparisonRequest(BaseModel): prior:dict[str,Any]; current:dict[str,Any]
class PropagationReadinessRequest(BaseModel): required_entity_ids:list[str]=Field(default_factory=list); completed_entity_ids:list[str]=Field(default_factory=list)
class ControlRedesignRecommendationRequest(BaseModel): intervention_program_id:str; control_id:str; current_design:dict[str,Any]=Field(default_factory=dict); recurrence_evidence:list[str]=Field(default_factory=list)
class IndependentRevalidationRequest(BaseModel): intervention_program_id:str; reviewer_role:str; result:str; rationale:str; evidence_refs:list[str]=Field(default_factory=list); tested_entity_ids:list[str]=Field(default_factory=list)
class SecondSystemicRecurrenceRequest(BaseModel): history:list[dict[str,Any]]=Field(default_factory=list)
class SustainabilityResetRequest(BaseModel): severity:str="high"; recurrence_count:int=1; minimum_days:int|None=None
class ResidualRiskReassessmentRequest(BaseModel): reviewer_role:str; residual_systemic_risk_score:float; decision:str; rationale:str; evidence_refs:list[str]=Field(default_factory=list)
class ReclosureReadinessRequest(BaseModel):
    renewed_plan_human_approved:bool=False; all_milestones_complete:bool=False; cross_entity_remediation_complete:bool=False; regulator_commitments_reconciled:bool=False; evidence_complete:bool=False; independent_revalidation_passed:bool=False; sustainability_reset_complete:bool=False; human_residual_risk_reassessed:bool=False; second_systemic_recurrence_detected:bool=False
class ExecutiveRecertificationRequest(BaseModel): reviewer_role:str; decision:str; rationale:str; readiness_score:int; independent_revalidation_id:str; residual_risk_reassessment_id:str; evidence_refs:list[str]=Field(default_factory=list)
class ProgramReclosureRequest(BaseModel): reviewer_role:str; decision:str; rationale:str; executive_recertification_id:str; sustainability_reset:dict[str,Any]; evidence_refs:list[str]=Field(default_factory=list)
