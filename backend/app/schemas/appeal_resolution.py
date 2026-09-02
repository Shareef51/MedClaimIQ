from __future__ import annotations
from decimal import Decimal
from pydantic import BaseModel, Field
from app.domain.claims import HumanDecision
from app.domain.appeal_resolution import AppealFinalOutcome, AppealSecondReviewAction

class AppealDecisionPacketRequest(BaseModel):
    outcome:AppealFinalOutcome; controlling_decision:HumanDecision; rationale:str=Field(min_length=20,max_length=12000); reason_codes:list[str]=Field(min_length=1,max_length=20); citation_refs:list[str]=Field(min_length=1,max_length=100); resolved_comparison_refs:list[str]=Field(default_factory=list,max_length=100); annotation_refs:list[str]=Field(default_factory=list,max_length=100); checkpoint_refs:list[str]=Field(default_factory=list,max_length=100); reconsidered_approved_amount:Decimal=Field(ge=0); recommendation_disagreement_reason:str|None=Field(default=None,max_length=5000); expected_appeal_version:int=Field(ge=1); expected_packet_version:int|None=Field(default=None,ge=1); idempotency_key:str=Field(min_length=8,max_length=180)
class AppealPacketLockRequest(BaseModel): expected_packet_version:int=Field(ge=1); idempotency_key:str=Field(min_length=8,max_length=180)
class AppealSecondReviewRequest(BaseModel): action:AppealSecondReviewAction; rationale:str=Field(min_length=20,max_length=5000); expected_packet_version:int=Field(ge=1); idempotency_key:str=Field(min_length=8,max_length=180)
class AppealFinalCloseRequest(BaseModel): expected_packet_version:int=Field(ge=1); expected_appeal_version:int=Field(ge=1); idempotency_key:str=Field(min_length=8,max_length=180)
class AppealNoticeReleaseRequest(BaseModel): idempotency_key:str=Field(min_length=8,max_length=180)
