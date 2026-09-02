from typing import Any
from pydantic import BaseModel,Field

class AssuranceExceptionRequest(BaseModel):
    sample_id:str; test_run_id:str; control_id:str; entity_id:str|None=None
    exception_type:str=Field(pattern="^(control_failure|insufficient_evidence|policy_deviation|timing_failure|data_quality|other)$")
    deficiency_kind:str=Field(pattern="^(design|operating|sustainability)$")
    severity_score:int=Field(ge=0,le=100)
    evidence_refs:list[dict[str,Any]]=Field(default_factory=list)
    provenance:dict[str,Any]=Field(default_factory=dict)

class AggregateDeficiencyRequest(BaseModel):
    control_id:str
    deficiency_kind:str=Field(pattern="^(design|operating|sustainability)$")
    exception_ids:list[str]=Field(min_length=1)
    affected_entities:list[str]=Field(default_factory=list)
    compensating_control:dict[str,Any]=Field(default_factory=dict)
    remediation_refs:list[dict[str,Any]]=Field(default_factory=list)

class EscalateEnterpriseIssueRequest(BaseModel):
    deficiency_key:str
    rationale:str=Field(min_length=30)

class DeficiencyClosureRequest(BaseModel):
    retest_refs:list[dict[str,Any]]=Field(min_length=1)
    conclusion:str=Field(pattern="^(remediated|not_remediated|partially_remediated|inconclusive)$")
    rationale:str=Field(min_length=30)
