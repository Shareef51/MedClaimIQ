from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.v1.rag import _authorize_claim_read, _identity
from app.db.session import get_db
from app.domain.access import Permission, ROLE_PERMISSIONS, UserRole
from app.domain.post_decision import post_decision_contract
from app.schemas.post_decision import (
    AppealAssignRequest, AppealCreateRequest, AppealReopenRequest, AppealResolveRequest,
    CorrespondenceCreateRequest, DecisionNoticeCreateRequest, DecisionNoticeReleaseRequest,
    DeliveryAttemptRequest, SupplementalEvidenceLinkRequest,
)
from app.services.post_decision import PostDecisionService
from app.services.review_workbench import ReviewConflictError, ReviewLockError

router=APIRouter(tags=["post-decision-communications-appeals"])


def _reviewer(request:Request):
    identity=_identity(request)
    if Permission.CLAIM_REVIEW not in ROLE_PERMISSIONS[identity.principal.role]: raise HTTPException(403,"claim:review permission is required")
    return identity


def _final_reviewer(request:Request):
    identity=_reviewer(request)
    if Permission.CLAIM_RECORD_HUMAN_DECISION not in ROLE_PERMISSIONS[identity.principal.role]: raise HTTPException(403,"claim:record_human_decision permission is required")
    return identity


def _handle(exc:Exception):
    if isinstance(exc,LookupError): raise HTTPException(404,str(exc)) from exc
    if isinstance(exc,(ReviewConflictError,ReviewLockError)): raise HTTPException(409,str(exc)) from exc
    raise exc


@router.get("/post-decision-model")
def model(): return post_decision_contract()


@router.get("/claims/{claim_id}/post-decision")
def snapshot(claim_id:str,request:Request,db:Session=Depends(get_db)):
    identity=_reviewer(request); _authorize_claim_read(db,identity,claim_id)
    try:return PostDecisionService(db,identity.principal.tenant_id).snapshot(claim_id)
    except Exception as exc:_handle(exc)


@router.get("/claims/{claim_id}/post-decision/tasks")
def task_queue(claim_id:str,request:Request,mine:bool=False,db:Session=Depends(get_db)):
    identity=_reviewer(request); _authorize_claim_read(db,identity,claim_id); svc=PostDecisionService(db,identity.principal.tenant_id)
    return [x for x in svc.task_queue(mine=identity.principal.user_id if mine else None,limit=200) if x["claim_id"]==claim_id]


@router.post("/claims/{claim_id}/post-decision/notices")
def create_notice(claim_id:str,payload:DecisionNoticeCreateRequest,request:Request,db:Session=Depends(get_db)):
    identity=_reviewer(request); _authorize_claim_read(db,identity,claim_id); svc=PostDecisionService(db,identity.principal.tenant_id)
    try:
        row=svc.create_notice(claim_id,payload.packet_id,identity.principal.user_id,audience=payload.audience,idempotency_key=payload.idempotency_key,trace_id=getattr(identity,"trace_id",None)); db.commit(); return svc.notice_view(row)
    except Exception as exc:db.rollback();_handle(exc)


@router.post("/claims/{claim_id}/post-decision/notices/{notice_id}/release")
def release_notice(claim_id:str,notice_id:str,payload:DecisionNoticeReleaseRequest,request:Request,db:Session=Depends(get_db)):
    identity=_final_reviewer(request); _authorize_claim_read(db,identity,claim_id); svc=PostDecisionService(db,identity.principal.tenant_id)
    try:
        row=svc.release_notice(claim_id,notice_id,identity.principal.user_id,idempotency_key=payload.idempotency_key,trace_id=getattr(identity,"trace_id",None)); db.commit(); return svc.notice_view(row)
    except Exception as exc:db.rollback();_handle(exc)




@router.get("/portal/claims/{claim_id}/post-decision")
def portal_post_decision(claim_id:str,request:Request,db:Session=Depends(get_db)):
    identity=_identity(request); _authorize_claim_read(db,identity,claim_id); svc=PostDecisionService(db,identity.principal.tenant_id)
    notices=[svc.notice_view(x) for x in svc.repo.notices(claim_id) if x.released_at is not None and x.audience in {"patient","provider","authorized_representative"}]
    appeals=[svc.appeal_view(x) for x in svc.repo.appeals(claim_id)]
    for item in appeals:item.pop("statement",None)
    return {"claim_id":claim_id,"notices":notices,"appeals":appeals,"appeal_window_days":int(svc.policy.get("appeal_window_days",180)),"human_authority":{"ai_can_issue_or_overturn":False,"appeal_resolution_requires_independent_human":True}}

@router.post("/portal/claims/{claim_id}/appeals")
def submit_appeal(claim_id:str,payload:AppealCreateRequest,request:Request,db:Session=Depends(get_db)):
    identity=_identity(request); _authorize_claim_read(db,identity,claim_id)
    if identity.principal.role not in {UserRole.PATIENT,UserRole.PROVIDER,UserRole.HOSPITAL_ADMIN}: raise HTTPException(403,"portal appeal intake is limited to external claim participants")
    svc=PostDecisionService(db,identity.principal.tenant_id)
    try:
        row=svc.submit_appeal(claim_id,identity.principal.user_id,identity.principal.role.value,notice_id=payload.notice_id,grounds=payload.grounds,statement=payload.statement,late_filing_reason=payload.late_filing_reason,idempotency_key=payload.idempotency_key,trace_id=getattr(identity,"trace_id",None)); db.commit(); return svc.appeal_view(row)
    except Exception as exc:db.rollback();_handle(exc)


@router.post("/portal/claims/{claim_id}/appeals/{appeal_id}/supplemental-evidence")
def supplemental_evidence(claim_id:str,appeal_id:str,payload:SupplementalEvidenceLinkRequest,request:Request,db:Session=Depends(get_db)):
    identity=_identity(request); _authorize_claim_read(db,identity,claim_id)
    if identity.principal.role not in {UserRole.PATIENT,UserRole.PROVIDER,UserRole.HOSPITAL_ADMIN}: raise HTTPException(403,"portal supplemental evidence is limited to external claim participants")
    svc=PostDecisionService(db,identity.principal.tenant_id)
    try:
        row=svc.link_supplemental_evidence(claim_id,appeal_id,payload.evidence_id,identity.principal.user_id,identity.principal.role.value,idempotency_key=payload.idempotency_key,trace_id=getattr(identity,"trace_id",None)); db.commit(); return {"link_id":row.link_id,"evidence_id":row.evidence_id,"evidence_version":row.evidence_version,"content_sha256":row.content_sha256,"linked_at":row.linked_at}
    except Exception as exc:db.rollback();_handle(exc)


@router.get("/portal/claims/{claim_id}/appeals/{appeal_id}")
def portal_appeal(claim_id:str,appeal_id:str,request:Request,db:Session=Depends(get_db)):
    identity=_identity(request); _authorize_claim_read(db,identity,claim_id); svc=PostDecisionService(db,identity.principal.tenant_id)
    try:
        row=svc.repo.appeal(appeal_id)
        if row is None or row.claim_id!=claim_id: raise LookupError("appeal not found")
        view=svc.appeal_view(row); view.pop("statement",None); return view
    except Exception as exc:_handle(exc)


@router.post("/claims/{claim_id}/post-decision/appeals/{appeal_id}/assign")
def assign_appeal(claim_id:str,appeal_id:str,payload:AppealAssignRequest,request:Request,db:Session=Depends(get_db)):
    identity=_final_reviewer(request); _authorize_claim_read(db,identity,claim_id); svc=PostDecisionService(db,identity.principal.tenant_id)
    try:
        row=svc.assign_appeal(claim_id,appeal_id,identity.principal.user_id,payload.reviewer_user_id,assignment_reason=payload.assignment_reason,expected_appeal_version=payload.expected_appeal_version,idempotency_key=payload.idempotency_key,trace_id=getattr(identity,"trace_id",None)); db.commit(); return svc.appeal_view(row)
    except Exception as exc:db.rollback();_handle(exc)


@router.post("/claims/{claim_id}/post-decision/appeals/{appeal_id}/reopen")
def reopen_appeal(claim_id:str,appeal_id:str,payload:AppealReopenRequest,request:Request,db:Session=Depends(get_db)):
    identity=_final_reviewer(request); _authorize_claim_read(db,identity,claim_id); svc=PostDecisionService(db,identity.principal.tenant_id)
    try:
        row=svc.reopen_appeal(claim_id,appeal_id,identity.principal.user_id,expected_appeal_version=payload.expected_appeal_version,rationale=payload.rationale,idempotency_key=payload.idempotency_key,trace_id=getattr(identity,"trace_id",None)); db.commit(); return svc.appeal_view(row)
    except Exception as exc:db.rollback();_handle(exc)


@router.post("/claims/{claim_id}/post-decision/appeals/{appeal_id}/resolve")
def resolve_appeal_retired(claim_id:str,appeal_id:str,payload:AppealResolveRequest,request:Request,db:Session=Depends(get_db)):
    # Release 39: direct resolution is intentionally retired because it bypasses
    # evidence-bound packet validation and dual control. Keep a 410 route so
    # stale clients fail closed rather than silently using weaker governance.
    raise HTTPException(status_code=410, detail="direct appeal resolution retired; use the governed /appeals/{appeal_id}/resolution packet workflow")


@router.post("/claims/{claim_id}/post-decision/correspondence")
def correspondence(claim_id:str,payload:CorrespondenceCreateRequest,request:Request,db:Session=Depends(get_db)):
    identity=_reviewer(request); _authorize_claim_read(db,identity,claim_id); svc=PostDecisionService(db,identity.principal.tenant_id)
    try:
        row=svc.record_correspondence(claim_id,identity.principal.user_id,direction=payload.direction,channel=payload.channel,audience=payload.audience,payload_sha256=payload.payload_sha256,idempotency_key=payload.idempotency_key,notice_id=payload.notice_id,appeal_id=payload.appeal_id,external_message_id=payload.external_message_id,actor_type="human"); db.commit(); return {"correspondence_id":row.correspondence_id,"occurred_at":row.occurred_at}
    except Exception as exc:db.rollback();_handle(exc)


@router.post("/claims/{claim_id}/post-decision/deliveries/{notification_id}/attempt")
def delivery_attempt(claim_id:str,notification_id:str,payload:DeliveryAttemptRequest,request:Request,db:Session=Depends(get_db)):
    identity=_reviewer(request); _authorize_claim_read(db,identity,claim_id); svc=PostDecisionService(db,identity.principal.tenant_id)
    try:
        result=svc.record_delivery_attempt(claim_id,notification_id,channel=payload.channel,success=payload.success,provider_message_id=payload.provider_message_id,error_code=payload.error_code,error_detail=payload.error_detail,trace_id=getattr(identity,"trace_id",None)); db.commit(); return result
    except Exception as exc:db.rollback();_handle(exc)


@router.post("/post-decision/sla/evaluate")
def evaluate_sla(request:Request,db:Session=Depends(get_db)):
    identity=_reviewer(request); svc=PostDecisionService(db,identity.principal.tenant_id)
    try:result=svc.evaluate_sla();db.commit();return result
    except Exception as exc:db.rollback();_handle(exc)
