from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Request
import hashlib, hmac, json, os
from sqlalchemy.orm import Session
from app.api.v1.rag import _authorize_claim_read
from app.db.session import get_db
from app.domain.financial_handoff import financial_handoff_contract
from app.schemas.financial_handoff import *
from app.services.financial_handoff import FinancialHandoffService
from app.services.review_workbench import ReviewConflictError, ReviewLockError
router=APIRouter(tags=["financial-handoff"])
def _identity(request):
    i=getattr(request.state,"identity",None)
    if i is None:raise HTTPException(401,"authenticated identity is unavailable")
    return i
def _handle(exc):
    if isinstance(exc,LookupError):raise HTTPException(404,str(exc)) from exc
    if isinstance(exc,(ReviewConflictError,ReviewLockError)):raise HTTPException(409,str(exc)) from exc
    if isinstance(exc,(ValueError,PermissionError)):raise HTTPException(400,str(exc)) from exc
    raise exc
@router.get("/financial-handoff-model")
def model():return financial_handoff_contract()
@router.get("/claims/{claim_id}/financial-handoff")
def snapshot(claim_id:str,request:Request,db:Session=Depends(get_db)):
    i=_identity(request);_authorize_claim_read(db,i,claim_id)
    try:return FinancialHandoffService(db,i.principal.tenant_id).snapshot(claim_id)
    except Exception as exc:_handle(exc)

@router.get("/claims/{claim_id}/financial-handoff/traceability")
def traceability(claim_id:str,request:Request,db:Session=Depends(get_db)):
    i=_identity(request);_authorize_claim_read(db,i,claim_id)
    try:return FinancialHandoffService(db,i.principal.tenant_id).traceability(claim_id)
    except Exception as exc:_handle(exc)

@router.post("/claims/{claim_id}/financial-handoff/packet")
def prepare(claim_id:str,payload:FinancialPacketPrepareRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request);_authorize_claim_read(db,i,claim_id);svc=FinancialHandoffService(db,i.principal.tenant_id)
    try:r=svc.prepare_packet(claim_id,i.principal.user_id,expected_packet_version=payload.expected_packet_version,idempotency_key=payload.idempotency_key,trace_id=getattr(request.state,"trace_id",None));db.commit();return svc.packet_view(r)
    except Exception as exc:db.rollback();_handle(exc)
@router.post("/claims/{claim_id}/financial-handoff/packets/{packet_id}/lock")
def lock(claim_id:str,packet_id:str,payload:FinancialPacketLockRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request);_authorize_claim_read(db,i,claim_id);svc=FinancialHandoffService(db,i.principal.tenant_id)
    try:r=svc.lock_packet(claim_id,packet_id,i.principal.user_id,expected_packet_version=payload.expected_packet_version,idempotency_key=payload.idempotency_key,trace_id=getattr(request.state,"trace_id",None));db.commit();return svc.packet_view(r)
    except Exception as exc:db.rollback();_handle(exc)
@router.post("/claims/{claim_id}/financial-handoff/packets/{packet_id}/authorize")
def authorize(claim_id:str,packet_id:str,payload:FinancialPacketAuthorizeRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request);_authorize_claim_read(db,i,claim_id);svc=FinancialHandoffService(db,i.principal.tenant_id)
    try:r=svc.authorize_packet(claim_id,packet_id,i.principal.user_id,rationale=payload.rationale,idempotency_key=payload.idempotency_key,trace_id=getattr(request.state,"trace_id",None));db.commit();return svc.packet_view(r)
    except Exception as exc:db.rollback();_handle(exc)
@router.post("/claims/{claim_id}/financial-handoff/packets/{packet_id}/payment-intent")
def stage(claim_id:str,packet_id:str,payload:PaymentIntentStageRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request);_authorize_claim_read(db,i,claim_id);svc=FinancialHandoffService(db,i.principal.tenant_id)
    try:r=svc.stage_payment_intent(claim_id,packet_id,i.principal.user_id,payee_ref=payload.payee_ref,idempotency_key=payload.idempotency_key,trace_id=getattr(request.state,"trace_id",None));db.commit();return {"payment_intent_id":r.payment_intent_id,"status":r.status,"amount":str(r.amount),"currency":r.currency}
    except Exception as exc:db.rollback();_handle(exc)
@router.post("/claims/{claim_id}/financial-handoff/payment-intents/{payment_intent_id}/handoff")
def handoff(claim_id:str,payment_intent_id:str,payload:PaymentHandoffRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request);_authorize_claim_read(db,i,claim_id);svc=FinancialHandoffService(db,i.principal.tenant_id)
    try:r=svc.handoff(claim_id,payment_intent_id,adapter_name=payload.adapter_name,actor_id=i.principal.user_id,idempotency_key=payload.idempotency_key,trace_id=getattr(request.state,"trace_id",None));db.commit();return {"handoff_id":r.handoff_id,"external_instruction_id":r.external_instruction_id,"status":r.status}
    except Exception as exc:db.rollback();_handle(exc)
@router.post("/claims/{claim_id}/financial-handoff/holds")
def hold(claim_id:str,payload:PaymentHoldRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request);_authorize_claim_read(db,i,claim_id);svc=FinancialHandoffService(db,i.principal.tenant_id)
    try:r=svc.place_hold(claim_id,i.principal.user_id,hold_type=payload.hold_type,reason_code=payload.reason_code,rationale=payload.rationale,idempotency_key=payload.idempotency_key);db.commit();return {"hold_id":r.hold_id,"active":r.active,"reason_code":r.reason_code}
    except Exception as exc:db.rollback();_handle(exc)
@router.post("/claims/{claim_id}/financial-handoff/holds/{hold_id}/release")
def release_hold(claim_id:str,hold_id:str,payload:HoldReleaseRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request);_authorize_claim_read(db,i,claim_id);svc=FinancialHandoffService(db,i.principal.tenant_id)
    try:r=svc.release_hold(claim_id,hold_id,i.principal.user_id,rationale=payload.rationale,idempotency_key=payload.idempotency_key);db.commit();return {"hold_id":r.hold_id,"active":r.active}
    except Exception as exc:db.rollback();_handle(exc)
@router.post("/claims/{claim_id}/financial-handoff/payment-intents/{payment_intent_id}/settlement")
def settlement(claim_id:str,payment_intent_id:str,payload:SettlementIngestRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request);_authorize_claim_read(db,i,claim_id);svc=FinancialHandoffService(db,i.principal.tenant_id)
    try:r=svc.ingest_settlement(claim_id,payment_intent_id,provider_event_id=payload.provider_event_id,status=payload.status.value,settled_amount=payload.settled_amount,currency=payload.currency,external_reference=payload.external_reference,payload=payload.payload,actor_user_id=i.principal.user_id);db.commit();return {"settlement_event_id":r.settlement_event_id,"status":r.status}
    except Exception as exc:db.rollback();_handle(exc)
@router.post("/claims/{claim_id}/financial-handoff/payment-intents/{payment_intent_id}/void-reissue")
def request_vr(claim_id:str,payment_intent_id:str,payload:VoidReissueRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request);_authorize_claim_read(db,i,claim_id);svc=FinancialHandoffService(db,i.principal.tenant_id)
    try:r=svc.request_void_reissue(claim_id,payment_intent_id,i.principal.user_id,action=payload.action,reason=payload.reason,idempotency_key=payload.idempotency_key);db.commit();return {"request_id":r.request_id,"status":r.status,"action":r.action}
    except Exception as exc:db.rollback();_handle(exc)
@router.post("/claims/{claim_id}/financial-handoff/void-reissue/{request_id}/approve")
def approve_vr(claim_id:str,request_id:str,payload:VoidReissueApproveRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request);_authorize_claim_read(db,i,claim_id);svc=FinancialHandoffService(db,i.principal.tenant_id)
    try:r=svc.approve_void_reissue(claim_id,request_id,i.principal.user_id,idempotency_key=payload.idempotency_key);db.commit();return {"request_id":r.request_id,"status":r.status,"action":r.action}
    except Exception as exc:db.rollback();_handle(exc)

@router.post("/financial/webhooks/settlement")
async def settlement_webhook(request:Request,db:Session=Depends(get_db)):
    secret=os.getenv("FINANCIAL_SETTLEMENT_WEBHOOK_SECRET","")
    if not secret: raise HTTPException(503,"financial settlement webhook secret is not configured")
    raw=await request.body(); supplied=request.headers.get("x-medclaimiq-financial-signature","")
    expected=hmac.new(secret.encode(),raw,hashlib.sha256).hexdigest()
    if not hmac.compare_digest(supplied,expected): raise HTTPException(401,"invalid financial settlement signature")
    try: body=json.loads(raw)
    except Exception as exc: raise HTTPException(400,"invalid settlement payload") from exc
    required={"tenant_id","claim_id","payment_intent_id","provider_event_id","status"}
    if not required.issubset(body): raise HTTPException(400,"missing settlement fields")
    svc=FinancialHandoffService(db,str(body["tenant_id"]))
    try:
        r=svc.ingest_settlement(str(body["claim_id"]),str(body["payment_intent_id"]),provider_event_id=str(body["provider_event_id"]),status=str(body["status"]),settled_amount=body.get("settled_amount"),currency=body.get("currency"),external_reference=body.get("external_reference"),payload=body);db.commit();return {"settlement_event_id":r.settlement_event_id,"status":r.status}
    except Exception as exc: db.rollback();_handle(exc)
