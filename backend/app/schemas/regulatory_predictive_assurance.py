from pydantic import BaseModel,Field
from typing import Any
class PredictiveForecastRequest(BaseModel):
    snapshot_id:str
    horizon_days:int=Field(default=90,ge=7,le=730)
    model_version:str=Field(default="reg-risk-forecast-v1",min_length=3)
class ScenarioSimulationRequest(BaseModel):
    scenario_key:str
    scenario_type:str
    assumptions:dict[str,Any]=Field(default_factory=dict)
class PredictiveReviewRequest(BaseModel):
    disposition:str
    rationale:str=Field(min_length=20)
    selected_management_actions:list[dict[str,Any]]=Field(default_factory=list)
