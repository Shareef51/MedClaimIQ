from pydantic import BaseModel,ConfigDict,Field
class EvaluationRunRequest(BaseModel):
    model_config=ConfigDict(extra="forbid"); candidate_version:str=Field(min_length=1,max_length=120); dataset:str="golden_claims_v1"
class MetricResponse(BaseModel):metric:str;value:float;threshold:float|None;passed:bool;suite:str
class EvaluationRunResponse(BaseModel):run_id:str;dataset_version:str;candidate_version:str;decision:str;pass_rate:float;metrics:list[MetricResponse];regression_reasons:list[str]
class EvaluationRunListItem(BaseModel):run_id:str;dataset_version:str;candidate_version:str;decision:str;pass_rate:float
