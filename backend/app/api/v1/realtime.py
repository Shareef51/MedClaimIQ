from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from pydantic import BaseModel, Field
from hashlib import sha256
from app.realtime.replay import EventReplayService
from sqlalchemy.orm import Session
from app.api.v1.rag import _authorize_claim_read, _identity
from app.db.session import get_db
from app.domain.access import Permission, ROLE_PERMISSIONS
from app.models.realtime import EventConsumerReceiptModel, EventDeadLetterModel, RealtimeOutboxModel
from app.realtime.streaming import ClaimRealtimeStreamer

router=APIRouter(tags=["realtime-events"])

@router.get("/realtime-model")
def realtime_model():
    return {"broker":"Redpanda/Kafka API","event_envelope_version":"1.0","partitioning":"claim_id","topics":["medclaimiq.claim.events.v1","medclaimiq.evidence.events.v1","medclaimiq.healthcare.events.v1","medclaimiq.agent.events.v1","medclaimiq.mcp.events.v1","medclaimiq.sla.events.v1"],"delivery":"at-least-once with idempotent consumers","outbox":{"transactional":True,"publisher":"SKIP LOCKED relay"},"retries":{"bounded":True,"dlq":True,"replay":True},"streaming":{"transport":"SSE","cursor":"stream_sequence"},"safety":{"raw_document_content_in_events":False,"tenant_claim_scope_preserved":True}}

@router.get("/claims/{claim_id}/realtime/events")
def stream(claim_id:str,request:Request,after_sequence:int=0,db:Session=Depends(get_db)):
    identity=_identity(request); _authorize_claim_read(db,identity,claim_id)
    streamer=ClaimRealtimeStreamer(request.app.state.session_factory_provider(),identity.principal.tenant_id,claim_id,after_sequence)
    return StreamingResponse(streamer.events(request.is_disconnected),media_type="text/event-stream",headers={"Cache-Control":"no-store","X-Accel-Buffering":"no"})

@router.get("/claims/{claim_id}/realtime/telemetry")
def telemetry(claim_id:str,request:Request,db:Session=Depends(get_db)):
    identity=_identity(request); _authorize_claim_read(db,identity,claim_id)
    tenant=identity.principal.tenant_id
    pending=db.scalar(select(func.count()).select_from(RealtimeOutboxModel).where(RealtimeOutboxModel.tenant_id==tenant,RealtimeOutboxModel.claim_id==claim_id,RealtimeOutboxModel.status.in_(["pending","retry"]))) or 0
    dlq=db.scalar(select(func.count()).select_from(EventDeadLetterModel).where(EventDeadLetterModel.tenant_id==tenant,EventDeadLetterModel.claim_id==claim_id)) or 0
    consumed=db.scalar(select(func.count()).select_from(EventConsumerReceiptModel).where(EventConsumerReceiptModel.tenant_id==tenant,EventConsumerReceiptModel.claim_id==claim_id,EventConsumerReceiptModel.status=="completed")) or 0
    return {"claim_id":claim_id,"outbox_pending":pending,"consumer_receipts":consumed,"dead_letters":dlq}


class ReplayBody(BaseModel):
    reason: str = Field(min_length=3, max_length=500)

@router.post("/claims/{claim_id}/realtime/dead-letters/{dead_letter_id}/replay")
def request_replay(claim_id:str, dead_letter_id:str, payload:ReplayBody, request:Request, db:Session=Depends(get_db)):
    identity=_identity(request); _authorize_claim_read(db,identity,claim_id)
    if Permission.CLAIM_REVIEW not in ROLE_PERMISSIONS[identity.principal.role]:
        raise HTTPException(status_code=403,detail="claim review permission is required for event replay")
    try:
        row=EventReplayService(db,identity.principal.tenant_id).request(dead_letter_id=dead_letter_id,user_id=identity.principal.user_id,reason=payload.reason)
        if row.claim_id != claim_id: raise ValueError("dead letter is not bound to requested claim")
        db.commit(); return {"replay_id":row.replay_id,"status":row.status,"target_topic":row.target_topic}
    except ValueError as exc:
        db.rollback(); raise HTTPException(status_code=404,detail=str(exc)) from exc

@router.get("/realtime/operations")
def operations(request:Request, db:Session=Depends(get_db)):
    identity=_identity(request)
    permissions=ROLE_PERMISSIONS[identity.principal.role]
    if Permission.SYSTEM_HEALTH_READ not in permissions and Permission.AUDIT_READ not in permissions:
        raise HTTPException(status_code=403,detail="system health or audit permission required")
    tenant=identity.principal.tenant_id
    rows=db.execute(select(RealtimeOutboxModel.status,func.count()).where(RealtimeOutboxModel.tenant_id==tenant).group_by(RealtimeOutboxModel.status)).all()
    topics=db.execute(select(RealtimeOutboxModel.topic,func.count()).where(RealtimeOutboxModel.tenant_id==tenant).group_by(RealtimeOutboxModel.topic)).all()
    dlq=db.scalar(select(func.count()).select_from(EventDeadLetterModel).where(EventDeadLetterModel.tenant_id==tenant)) or 0
    return {"outbox_by_status":dict(rows),"outbox_by_topic":dict(topics),"dead_letters":dlq}
