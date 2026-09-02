from __future__ import annotations
import hashlib, hmac, json
from datetime import datetime, timezone
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.db.session import get_db, set_tenant_context
from app.domain.realtime import EventEnvelope, EventTopic
from app.realtime.events import enqueue_realtime_event
from app.realtime.fhir_subscription import FHIRSubscriptionValidator

router=APIRouter(tags=["fhir-subscriptions"])

@router.post("/fhir/subscriptions/events")
async def subscription_event(request:Request, db:Session=Depends(get_db)):
    body=await request.body()
    tenant_id=request.headers.get("X-MedClaimIQ-Tenant-Id") or ""
    claim_id=request.headers.get("X-MedClaimIQ-Claim-Id") or ""
    signature=request.headers.get("X-FHIR-Webhook-Signature") or ""
    material=tenant_id.encode()+b"\n"+claim_id.encode()+b"\n"+body
    expected=hmac.new(get_settings().fhir_subscription_webhook_secret.get_secret_value().encode(),material,hashlib.sha256).hexdigest()
    if not tenant_id or not claim_id or not hmac.compare_digest(signature,expected):
        raise HTTPException(status_code=401,detail="invalid FHIR subscription signature")
    try: payload=json.loads(body); note=FHIRSubscriptionValidator().validate(payload)
    except Exception as exc: raise HTTPException(status_code=422,detail=str(exc)) from exc
    set_tenant_context(db,tenant_id)
    event_id=f"fsub_{uuid4().hex}"
    enqueue_realtime_event(db,envelope=EventEnvelope(event_id=event_id,event_type="healthcare.fhir.subscription.changed",tenant_id=tenant_id,claim_id=claim_id,aggregate_type=note.resource_type,aggregate_id=note.resource_id,occurred_at=datetime.now(timezone.utc),producer="medclaimiq-fhir-subscription-webhook",payload={"resource_type":note.resource_type,"resource_id":note.resource_id,"version_id":note.version_id,"subscription_id":note.subscription_id}),topic=EventTopic.HEALTHCARE.value)
    db.commit(); return {"accepted":True,"event_id":event_id}
