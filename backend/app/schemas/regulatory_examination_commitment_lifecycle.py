from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Any
class CommitmentRegisterCreate(BaseModel):
    source_commitment_id:str; examination_id:str; description:str; owner_user_id:str; due_at:str|None=None; control_id:str|None=None; obligation_id:str|None=None; normalized_theme:str|None=None; required_evidence_types:list[str]=Field(default_factory=list); source_type:str="confirmed_verbal"
class MilestoneCreate(BaseModel):
    commitment_id:str; title:str; owner_user_id:str; due_at:str|None=None; dependency_ids:list[str]=Field(default_factory=list); required_evidence_types:list[str]=Field(default_factory=list)
class EvidenceLinkCreate(BaseModel):
    commitment_id:str; milestone_id:str|None=None; evidence_id:str; evidence_type:str; version_id:str; sha256:str; source_ref:str|None=None
class EffectivenessValidationCreate(BaseModel):
    commitment_id:str; validator_user_id:str; validator_role:str; result:str; rationale:str; evidence_refs:list[str]=Field(default_factory=list)
class AmendmentRequest(BaseModel):
    commitment_id:str; change_type:str; proposed_value:Any; rationale:str; reviewer_role:str
class CompletionCertification(BaseModel):
    reviewer_role:str; decision:str; rationale:str; milestones:list[dict[str,Any]]=Field(default_factory=list); evidence:list[dict[str,Any]]=Field(default_factory=list); validations:list[dict[str,Any]]=Field(default_factory=list)
class FollowUpCreate(BaseModel):
    commitment_id:str; examination_id:str; regulator_reference:str|None=None; description:str; due_at:str|None=None; evidence_refs:list[str]=Field(default_factory=list)
class ReconciliationRequest(BaseModel):
    commitment:dict[str,Any]; written_records:list[dict[str,Any]]=Field(default_factory=list)
