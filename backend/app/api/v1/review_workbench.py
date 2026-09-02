from __future__ import annotations
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.v1.rag import _authorize_claim_read, _identity
from app.db.session import get_db
from app.domain.access import Permission, ROLE_PERMISSIONS
from app.schemas.review_workbench import ReviewDecisionRequest, ReviewEvidenceRequest, ReviewLockRequest, ReviewLockResponse, ReviewerNoteCreate, ReviewQueueItem
from app.services.review_workbench import ReviewConflictError, ReviewLockError, ReviewWorkbenchService
from app.db.session import get_session_factory
from app.realtime.streaming import TenantRealtimeStreamer

router = APIRouter(tags=["human-review-workbench"])


def _require(identity, permission: Permission):
    if permission not in ROLE_PERMISSIONS[identity.principal.role]:
        raise HTTPException(status_code=403, detail=f"{permission.value} permission is required")


def _reviewer(request: Request):
    identity=_identity(request); _require(identity, Permission.CLAIM_REVIEW); return identity


def _handle(exc: Exception):
    if isinstance(exc, LookupError): raise HTTPException(status_code=404, detail=str(exc)) from exc
    if isinstance(exc, (ReviewConflictError, ReviewLockError)): raise HTTPException(status_code=409, detail=str(exc)) from exc
    raise exc


@router.get("/review-model")
def review_model():
    return {
        "queue":"deterministic SLA/guardrail/contradiction-aware priority scoring",
        "concurrency":{"lease_lock":True,"hashed_lock_token":True,"optimistic_claim_status_version":True,"automatic_expiry":True},
        "workbench":["claim","evidence","citations","FHIR verification","GraphRAG","contradictions","agent findings","decision support","guardrails","MCP approvals","SLA timers","review notes","timeline"],
        "human_authority":{"final_decision_only_by_authorized_reviewer":True,"ai_recommendation_is_advisory":True,"override_reason_required":True},
        "audit":{"append_only_review_events":True,"immutable_decision_metadata":True,"realtime_events":True},
        "frontend":{"queue_sse":"/api/v1/review/queue/events","claim_sse":"/api/v1/claims/{claim_id}/realtime/events","browser_bearer_storage":False,"human_decision_only":True},
    }


@router.get("/review/queue/events")
def review_queue_events(request: Request, after_sequence: int = 0):
    identity = _reviewer(request)
    streamer = TenantRealtimeStreamer(
        get_session_factory(),
        identity.principal.tenant_id,
        after_sequence=after_sequence,
        event_prefixes=("review.", "sla.timer.", "sla.post_decision.", "rag.guardrail.", "agent.workflow.", "appeal.", "communication.", "financial_investigation.", "recovery.", "provider_dispute_intelligence.", "provider_dispute_resolution.", "recovery_settlement.", "recovery_settlement_intelligence.", "recovery_control_assurance.", "regulatory_transport.", "regulatory_supervision.", "regulatory_examination.", "regulatory_remediation.", "regulatory_portfolio."),
    )
    return StreamingResponse(
        streamer.events(request.is_disconnected),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-store", "X-Accel-Buffering": "no"},
    )


@router.get("/review/queue", response_model=list[ReviewQueueItem])
def review_queue(request: Request, mine: bool=False, limit: int=100, db: Session=Depends(get_db)):
    identity=_reviewer(request); svc=ReviewWorkbenchService(db, identity.principal.tenant_id)
    return svc.repo.list_queue(reviewer_user_id=identity.principal.user_id if mine else None, limit=limit)


@router.post("/review/queue/refresh", response_model=list[ReviewQueueItem])
def refresh_review_queue(request: Request, db: Session=Depends(get_db)):
    identity=_reviewer(request); svc=ReviewWorkbenchService(db, identity.principal.tenant_id)
    rows=svc.refresh_queue(); db.commit(); return rows


@router.get("/claims/{claim_id}/review/workbench")
def workbench(claim_id: str, request: Request, db: Session=Depends(get_db)):
    identity=_reviewer(request); _authorize_claim_read(db, identity, claim_id)
    try: return ReviewWorkbenchService(db, identity.principal.tenant_id).snapshot(claim_id)
    except Exception as exc: _handle(exc)


@router.post("/claims/{claim_id}/review/lock", response_model=ReviewLockResponse)
def acquire_lock(claim_id: str, payload: ReviewLockRequest, request: Request, db: Session=Depends(get_db)):
    identity=_reviewer(request); _authorize_claim_read(db, identity, claim_id)
    try:
        row, token=ReviewWorkbenchService(db, identity.principal.tenant_id).acquire_lock(claim_id, identity.principal.user_id, lease_seconds=payload.lease_seconds)
        db.commit(); return ReviewLockResponse(lock_id=row.lock_id,lock_token=token,lock_version=row.lock_version,locked_until=row.locked_until)
    except Exception as exc: db.rollback(); _handle(exc)


@router.post("/claims/{claim_id}/review/lock/renew")
def renew_lock(claim_id: str, payload: ReviewLockRequest, request: Request, x_review_lock_token: str=Header(alias="X-Review-Lock-Token"), db: Session=Depends(get_db)):
    identity=_reviewer(request); _authorize_claim_read(db, identity, claim_id)
    try:
        row=ReviewWorkbenchService(db, identity.principal.tenant_id).renew_lock(claim_id,identity.principal.user_id,x_review_lock_token,lease_seconds=payload.lease_seconds)
        db.commit(); return {"lock_id":row.lock_id,"lock_version":row.lock_version,"locked_until":row.locked_until}
    except Exception as exc: db.rollback(); _handle(exc)


@router.delete("/claims/{claim_id}/review/lock")
def release_lock(claim_id: str, request: Request, x_review_lock_token: str=Header(alias="X-Review-Lock-Token"), db: Session=Depends(get_db)):
    identity=_reviewer(request); _authorize_claim_read(db, identity, claim_id)
    try:
        ReviewWorkbenchService(db,identity.principal.tenant_id).release_lock(claim_id,identity.principal.user_id,x_review_lock_token); db.commit(); return {"released":True}
    except Exception as exc: db.rollback(); _handle(exc)


@router.post("/claims/{claim_id}/review/begin")
def begin_review(claim_id: str, request: Request, x_review_lock_token: str=Header(alias="X-Review-Lock-Token"), idempotency_key: str=Header(alias="Idempotency-Key"), db: Session=Depends(get_db)):
    identity=_reviewer(request); _authorize_claim_read(db, identity, claim_id)
    try:
        claim=ReviewWorkbenchService(db,identity.principal.tenant_id).begin_review(claim_id,identity.principal.user_id,x_review_lock_token,idempotency_key=idempotency_key,trace_id=getattr(identity,"trace_id",None)); db.commit()
        return {"claim_id":claim.claim_id,"status":claim.status,"status_version":claim.status_version}
    except Exception as exc: db.rollback(); _handle(exc)


@router.post("/claims/{claim_id}/review/notes")
def add_note(claim_id: str,payload: ReviewerNoteCreate,request: Request,x_review_lock_token: str=Header(alias="X-Review-Lock-Token"),db: Session=Depends(get_db)):
    identity=_reviewer(request); _authorize_claim_read(db, identity, claim_id)
    try:
        row=ReviewWorkbenchService(db,identity.principal.tenant_id).add_note(claim_id,identity.principal.user_id,x_review_lock_token,note_type=payload.note_type.value,body=payload.body,evidence_refs=payload.evidence_refs,idempotency_key=payload.idempotency_key,trace_id=getattr(identity,"trace_id",None)); db.commit()
        return {"note_id":row.note_id,"created_at":row.created_at}
    except Exception as exc: db.rollback(); _handle(exc)


@router.post("/claims/{claim_id}/review/request-evidence")
def request_evidence(claim_id: str,payload: ReviewEvidenceRequest,request: Request,x_review_lock_token: str=Header(alias="X-Review-Lock-Token"),db: Session=Depends(get_db)):
    identity=_reviewer(request); _authorize_claim_read(db, identity, claim_id); _require(identity,Permission.CLAIM_REQUEST_EVIDENCE)
    try:
        row=ReviewWorkbenchService(db,identity.principal.tenant_id).request_more_evidence(claim_id,identity.principal.user_id,x_review_lock_token,rationale=payload.rationale,requested_document_types=payload.requested_document_types,evidence_snapshot_ids=payload.evidence_snapshot_ids,idempotency_key=payload.idempotency_key,trace_id=getattr(identity,"trace_id",None)); db.commit()
        return {"decision_id":row.decision_id,"decision":row.decision}
    except Exception as exc: db.rollback(); _handle(exc)


@router.post("/claims/{claim_id}/review/decision")
def decision(claim_id: str,payload: ReviewDecisionRequest,request: Request,x_review_lock_token: str=Header(alias="X-Review-Lock-Token"),db: Session=Depends(get_db)):
    identity=_reviewer(request); _authorize_claim_read(db, identity, claim_id); _require(identity,Permission.CLAIM_RECORD_HUMAN_DECISION)
    raise HTTPException(status_code=409, detail="Direct human-decision endpoint is retired for adjudicative actions; use the governed-closure decision packet workflow")
