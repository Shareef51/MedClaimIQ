from pydantic import BaseModel,Field
from typing import Any
from datetime import datetime

class AssuranceObservationRequest(BaseModel):
    forecast_id:str
    observation_key:str=Field(min_length=3,max_length=140)
    signal_type:str
    control_id:str|None=None
    finding_id:str|None=None
    commitment_id:str|None=None
    observed_value:int=Field(ge=0,le=100)
    expected_value:int=Field(ge=0,le=100)
    evidence_age_days:int=Field(default=0,ge=0,le=3650)
    evidence_refs:list[dict[str,Any]]=Field(default_factory=list)
    observed_at:datetime
    threshold_version:str=Field(default="continuous-assurance-v1")

class AssuranceInvestigationRequest(BaseModel):
    disposition:str
    rationale:str=Field(min_length=20)
    corrective_response:list[dict[str,Any]]=Field(default_factory=list)
