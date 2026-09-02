from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.api.v1.rag import _authorize_claim_read
from app.db.session import get_db
from app.domain.appeal_resolution import appeal_resolution_contract
from app.schemas.appeal_resolution import AppealDecisionPacketRequest, AppealPacketLockRequest, AppealSecondReviewRequest, AppealFinalCloseRequest, AppealNoticeReleaseRequest
from app.services.appeal_resolution import AppealResolutionService
from app.services.post_decision import PostDecisionService
from app.services.review_workbench import ReviewConflictError, ReviewLockError
router=APIRouter(tags=["appeal-resolution"])
def _identity(request):
    i=getattr(request.state,"identity",None)
    if i is None: raise HTTPException(401,"authenticated identity is unavailable")
    return i
def _handle(exc):
    if isinstance(exc,LookupError): raise HTTPException(404,str(exc)) from exc
    if isinstance(exc,(ReviewConflictError,ReviewLockError)): raise HTTPException(409,str(exc)) from exc
    if isinstance(exc,(ValueError,PermissionError)): raise HTTPException(400,str(exc)) from exc
    raise exc
@router.get("/appeal-resolution-model")
def model(): return appeal_resolution_contract()
@router.get("/claims/{claim_id}/appeals/{appeal_id}/resolution")
def snapshot(claim_id:str,appeal_id:str,request:Request,db:Session=Depends(get_db)):
    i=_identity(request);_authorize_claim_read(db,i,claim_id)
    try:return AppealResolutionService(db,i.principal.tenant_id).snapshot(claim_id,appeal_id)
    except Exception as exc:_handle(exc)
@router.post("/claims/{claim_id}/appeals/{appeal_id}/resolution/packet")
def save_packet(claim_id:str,appeal_id:str,payload:AppealDecisionPacketRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request);_authorize_claim_read(db,i,claim_id);svc=AppealResolutionService(db,i.principal.tenant_id)
    try:
        row=svc.save_packet(claim_id,appeal_id,i.principal.user_id,outcome=payload.outcome,controlling_decision=payload.controlling_decision,rationale=payload.rationale,reason_codes=payload.reason_codes,citation_refs=payload.citation_refs,resolved_comparison_refs=payload.resolved_comparison_refs,annotation_refs=payload.annotation_refs,checkpoint_refs=payload.checkpoint_refs,reconsidered_approved_amount=payload.reconsidered_approved_amount,recommendation_disagreement_reason=payload.recommendation_disagreement_reason,expected_appeal_version=payload.expected_appeal_version,expected_packet_version=payload.expected_packet_version,idempotency_key=payload.idempotency_key,trace_id=getattr(request.state,"trace_id",None));db.commit();return svc.packet_view(row)
    except Exception as exc:db.rollback();_handle(exc)
@router.post("/claims/{claim_id}/appeals/{appeal_id}/resolution/packets/{packet_id}/lock")
def lock(claim_id:str,appeal_id:str,packet_id:str,payload:AppealPacketLockRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request);_authorize_claim_read(db,i,claim_id);svc=AppealResolutionService(db,i.principal.tenant_id)
    try:row=svc.lock_packet(claim_id,appeal_id,packet_id,i.principal.user_id,expected_packet_version=payload.expected_packet_version,idempotency_key=payload.idempotency_key,trace_id=getattr(request.state,"trace_id",None));db.commit();return svc.packet_view(row)
    except Exception as exc:db.rollback();_handle(exc)
@router.post("/claims/{claim_id}/appeals/{appeal_id}/resolution/packets/{packet_id}/second-review")
def second_review(claim_id:str,appeal_id:str,packet_id:str,payload:AppealSecondReviewRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request);_authorize_claim_read(db,i,claim_id);svc=AppealResolutionService(db,i.principal.tenant_id)
    try:row=svc.second_review(claim_id,appeal_id,packet_id,i.principal.user_id,action=payload.action,rationale=payload.rationale,expected_packet_version=payload.expected_packet_version,idempotency_key=payload.idempotency_key,trace_id=getattr(request.state,"trace_id",None));db.commit();return svc.packet_view(row)
    except Exception as exc:db.rollback();_handle(exc)
@router.post("/claims/{claim_id}/appeals/{appeal_id}/resolution/packets/{packet_id}/close")
def close(claim_id:str,appeal_id:str,packet_id:str,payload:AppealFinalCloseRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request);_authorize_claim_read(db,i,claim_id);svc=AppealResolutionService(db,i.principal.tenant_id)
    try:r=svc.close(claim_id,appeal_id,packet_id,i.principal.user_id,expected_packet_version=payload.expected_packet_version,expected_appeal_version=payload.expected_appeal_version,idempotency_key=payload.idempotency_key,trace_id=getattr(request.state,"trace_id",None));db.commit();return svc.snapshot(claim_id,appeal_id)
    except Exception as exc:db.rollback();_handle(exc)
@router.post("/claims/{claim_id}/appeals/{appeal_id}/resolution/notices/{notice_id}/release")
def release_notice(claim_id:str,appeal_id:str,notice_id:str,payload:AppealNoticeReleaseRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request);_authorize_claim_read(db,i,claim_id)
    try:row=PostDecisionService(db,i.principal.tenant_id).release_notice(claim_id,notice_id,i.principal.user_id,idempotency_key=payload.idempotency_key,trace_id=getattr(request.state,"trace_id",None));db.commit();return {"notice_id":row.notice_id,"status":row.status,"appeal_id":row.appeal_id,"resolution_id":row.resolution_id}
    except Exception as exc:db.rollback();_handle(exc)
