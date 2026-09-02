from __future__ import annotations
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.v1.rag import _authorize_claim_read, _identity
from app.db.session import get_db
from app.domain.access import Permission, ROLE_PERMISSIONS
from app.domain.governed_closure import governed_closure_contract
from app.schemas.governed_closure import DecisionCloseRequest, DecisionPacketUpsertRequest, DecisionPacketValidateRequest, SecondReviewRequest
from app.services.governed_closure import GovernedClosureService
from app.services.review_workbench import ReviewConflictError, ReviewLockError

router=APIRouter(tags=["governed-human-claim-closure"])


def _reviewer(request: Request):
    identity=_identity(request)
    if Permission.CLAIM_REVIEW not in ROLE_PERMISSIONS[identity.principal.role]:
        raise HTTPException(status_code=403,detail="claim:review permission is required")
    return identity


def _final_reviewer(request: Request):
    identity=_reviewer(request)
    if Permission.CLAIM_RECORD_HUMAN_DECISION not in ROLE_PERMISSIONS[identity.principal.role]:
        raise HTTPException(status_code=403,detail="claim:record_human_decision permission is required")
    return identity


def _handle(exc: Exception):
    if isinstance(exc,LookupError): raise HTTPException(status_code=404,detail=str(exc)) from exc
    if isinstance(exc,(ReviewConflictError,ReviewLockError)): raise HTTPException(status_code=409,detail=str(exc)) from exc
    raise exc


@router.get("/governed-closure-model")
def governed_closure_model():
    body=governed_closure_contract()
    body["governance"]={"mandatory_reason_codes":True,"mandatory_rationale":True,"ai_disagreement_capture":True,"partial_approval":True,"immutable_hash_chained_audit":True,"checkpoint_resolution":True,"evidence_snapshot_binding":True,"sse_status_propagation":True}
    return body


@router.get("/claims/{claim_id}/review/governed-closure")
def snapshot(claim_id: str,request: Request,db: Session=Depends(get_db)):
    identity=_reviewer(request); _authorize_claim_read(db,identity,claim_id)
    try: return GovernedClosureService(db,identity.principal.tenant_id).snapshot(claim_id)
    except Exception as exc: _handle(exc)


@router.post("/claims/{claim_id}/review/governed-closure/packets")
def save_packet(claim_id: str,payload: DecisionPacketUpsertRequest,request: Request,x_review_lock_token: str=Header(alias="X-Review-Lock-Token"),db: Session=Depends(get_db)):
    identity=_final_reviewer(request); _authorize_claim_read(db,identity,claim_id); svc=GovernedClosureService(db,identity.principal.tenant_id)
    try:
        row=svc.save_packet(claim_id,identity.principal.user_id,x_review_lock_token,decision=payload.decision,rationale=payload.rationale,reason_codes=[x.value for x in payload.reason_codes],evidence_snapshot_ids=payload.evidence_snapshot_ids,finding_refs=payload.finding_refs,annotation_refs=payload.annotation_refs,inconsistency_refs=payload.inconsistency_refs,checkpoint_refs=payload.checkpoint_refs,approved_amount=payload.approved_amount,partial_line_decisions=[x.model_dump(mode="json") for x in payload.partial_line_decisions],ai_disagreement_reason=payload.ai_disagreement_reason,escalation_queue=payload.escalation_queue,expected_claim_status_version=payload.expected_claim_status_version,expected_packet_version=payload.expected_packet_version,idempotency_key=payload.idempotency_key,trace_id=getattr(identity,"trace_id",None))
        db.commit(); return svc.packet_view(row)
    except Exception as exc: db.rollback(); _handle(exc)


@router.post("/claims/{claim_id}/review/governed-closure/packets/{packet_id}/validate")
def validate_packet(claim_id: str,packet_id: str,payload: DecisionPacketValidateRequest,request: Request,x_review_lock_token: str=Header(alias="X-Review-Lock-Token"),db: Session=Depends(get_db)):
    identity=_final_reviewer(request); _authorize_claim_read(db,identity,claim_id); svc=GovernedClosureService(db,identity.principal.tenant_id)
    try:
        row=svc.validate_and_lock(claim_id,packet_id,identity.principal.user_id,x_review_lock_token,expected_packet_version=payload.expected_packet_version,idempotency_key=payload.idempotency_key,trace_id=getattr(identity,"trace_id",None)); db.commit(); return svc.packet_view(row)
    except Exception as exc: db.rollback(); _handle(exc)


@router.post("/claims/{claim_id}/review/governed-closure/packets/{packet_id}/second-review")
def second_review(claim_id: str,packet_id: str,payload: SecondReviewRequest,request: Request,db: Session=Depends(get_db)):
    identity=_final_reviewer(request); _authorize_claim_read(db,identity,claim_id); svc=GovernedClosureService(db,identity.principal.tenant_id)
    try:
        row=svc.second_review(claim_id,packet_id,identity.principal.user_id,action=payload.action,rationale=payload.rationale,expected_packet_version=payload.expected_packet_version,idempotency_key=payload.idempotency_key,trace_id=getattr(identity,"trace_id",None)); db.commit(); return svc.packet_view(row)
    except Exception as exc: db.rollback(); _handle(exc)


@router.post("/claims/{claim_id}/review/governed-closure/packets/{packet_id}/close")
def close_packet(claim_id: str,packet_id: str,payload: DecisionCloseRequest,request: Request,x_review_lock_token: str=Header(alias="X-Review-Lock-Token"),db: Session=Depends(get_db)):
    identity=_final_reviewer(request); _authorize_claim_read(db,identity,claim_id); svc=GovernedClosureService(db,identity.principal.tenant_id)
    try:
        row=svc.close(claim_id,packet_id,identity.principal.user_id,x_review_lock_token,expected_packet_version=payload.expected_packet_version,expected_claim_status_version=payload.expected_claim_status_version,idempotency_key=payload.idempotency_key,trace_id=getattr(identity,"trace_id",None)); db.commit(); return svc.packet_view(row)
    except Exception as exc: db.rollback(); _handle(exc)


@router.get("/claims/{claim_id}/review/governed-closure/traceability")
def traceability(claim_id: str,request: Request,packet_id: str | None=None,db: Session=Depends(get_db)):
    identity=_reviewer(request); _authorize_claim_read(db,identity,claim_id)
    try: return GovernedClosureService(db,identity.principal.tenant_id).traceability(claim_id,packet_id)
    except Exception as exc: _handle(exc)
