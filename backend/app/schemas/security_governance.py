from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel,ConfigDict,Field

class RetentionPolicyCreate(BaseModel):
    model_config=ConfigDict(extra="forbid")
    policy_key:str=Field(min_length=2,max_length=120); version:str=Field(min_length=1,max_length=40); resource_type:str=Field(min_length=2,max_length=80); classification:str; retention_days:int=Field(ge=1,le=36500); disposition:str="review_then_delete"

class DispositionRequestCreate(BaseModel):
    model_config=ConfigDict(extra="forbid")
    policy_id:str; resource_type:str; resource_id:str; classification:str; reason:str=Field(min_length=8,max_length=2000); idempotency_key:str=Field(min_length=8,max_length=160); dry_run:bool=True

class AuditExportRequest(BaseModel):
    model_config=ConfigDict(extra="forbid")
    from_time:datetime; to_time:datetime


class KeyReferenceCreate(BaseModel):
    model_config=ConfigDict(extra="forbid")
    provider:str=Field(min_length=2,max_length=40)
    purpose:str=Field(min_length=2,max_length=80)
    external_key_id:str=Field(min_length=3,max_length=512)
    rotation_days:int=Field(default=365,ge=30,le=3650)
