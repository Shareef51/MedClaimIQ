from datetime import datetime
from typing import Any
from pydantic import BaseModel,Field

class ControlTestPlanRequest(BaseModel):
    control_id:str
    test_type:str=Field(pattern="^(design_effectiveness|operating_effectiveness|sustainability)$")
    frequency:str=Field(default="monthly")
    sampling_strategy:dict[str,Any]=Field(default_factory=dict)
    evidence_requirements:list[dict[str,Any]]=Field(default_factory=list)
    independent_tester_role:str=Field(default="auditor")

class ControlTestRunRequest(BaseModel):
    test_plan_id:str
    test_window_start:datetime
    test_window_end:datetime
    population:list[dict[str,Any]]=Field(min_length=1)
    sample_size:int=Field(default=25,ge=1,le=1000)

class SampleResultRequest(BaseModel):
    result:str=Field(pattern="^(pass|fail|exception|insufficient_evidence)$")
    evidence_refs:list[dict[str,Any]]=Field(default_factory=list)
    exception_code:str|None=None

class IndependentConclusionRequest(BaseModel):
    effectiveness:str=Field(pattern="^(effective|effective_with_exceptions|ineffective|inconclusive)$")
    rationale:str=Field(min_length=30)
