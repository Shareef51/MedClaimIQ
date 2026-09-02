from __future__ import annotations

import hashlib
import hmac
import json
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.v1.rag import _authorize_claim_read, _identity
from app.core.config import get_settings
from app.db.session import get_db
from app.domain.access import Permission, ROLE_PERMISSIONS, UserRole
from app.domain.communication_delivery import communication_delivery_contract
from app.schemas.communication_delivery import (
    EndpointUpsertRequest, LegalHoldCreateRequest, LegalHoldReleaseRequest, QueueNoticeRequest,
    RecoveryRequest, ReconcileRequest, TemplateApproveRequest, TemplateCreateRequest,
    WebhookReceiptRequest, WorkerExecuteRequest, WorkerLeaseRequest,
)
from app.services.communication_delivery import CommunicationDeliveryService
from app.services.review_workbench import ReviewConflictError, ReviewLockError

router=APIRouter(tags=["communication-delivery-compliance"])
settings=get_settings()


def _reviewer(request:Request):
    identity=_identity(request)
    if Permission.CLAIM_REVIEW not in ROLE_PERMISSIONS[identity.principal.role]: raise HTTPException(403,"claim:review permission is required")
    return identity


def _handle(exc:Exception):
    if isinstance(exc,LookupError): raise HTTPException(404,str(exc)) from exc
    if isinstance(exc,(ReviewConflictError,ReviewLockError,ValueError)): raise HTTPException(409,str(exc)) from exc
    raise exc


def _require_worker_token(token:str|None):
    expected=settings.communication_worker_token.get_secret_value()
    if not token or not hmac.compare_digest(token,expected): raise HTTPException(401,"invalid communication worker credential")


@router.get("/communication-delivery-model")
def model(): return communication_delivery_contract()


@router.put("/claims/{claim_id}/communications/endpoints")
def upsert_endpoint(claim_id:str,payload:EndpointUpsertRequest,request:Request,db:Session=Depends(get_db)):
    identity=_identity(request); _authorize_claim_read(db,identity,claim_id); svc=CommunicationDeliveryService(db,identity.principal.tenant_id)
    allowed_audiences={
        UserRole.PATIENT:{"patient"},
        UserRole.PROVIDER:{"provider"},
        UserRole.HOSPITAL_ADMIN:{"provider"},
        UserRole.CLAIMS_REVIEWER:{"patient","provider","authorized_representative"},
    }.get(identity.principal.role,set())
    if payload.audience not in allowed_audiences: raise HTTPException(403,"caller cannot manage that communication audience")
    try:
        row=svc.upsert_endpoint(claim_id,identity.principal.user_id,audience=payload.audience,channel=payload.channel.value,destination=payload.destination,consent_status=payload.consent_status.value,locale=payload.locale,accessibility_preferences=payload.accessibility_preferences); db.commit(); return svc.endpoint_view(row)
    except Exception as exc: db.rollback(); _handle(exc)


@router.post("/communications/templates")
def create_template(payload:TemplateCreateRequest,request:Request,db:Session=Depends(get_db)):
    identity=_reviewer(request); svc=CommunicationDeliveryService(db,identity.principal.tenant_id)
    try:
        row=svc.create_template(identity.principal.user_id,template_key=payload.template_key,template_version=payload.template_version,locale=payload.locale,channel=payload.channel.value,subject_template=payload.subject_template,body_template=payload.body_template,accessibility_schema=payload.accessibility_schema,change_reason=payload.change_reason); db.commit(); return {"template_id":row.template_id,"status":row.status,"content_sha256":row.content_sha256}
    except Exception as exc: db.rollback(); _handle(exc)


@router.post("/communications/templates/{template_id}/approve")
def approve_template(template_id:str,payload:TemplateApproveRequest,request:Request,db:Session=Depends(get_db)):
    identity=_reviewer(request); svc=CommunicationDeliveryService(db,identity.principal.tenant_id)
    try:
        row=svc.approve_template(template_id,identity.principal.user_id,approval_reason=payload.approval_reason); db.commit(); return {"template_id":row.template_id,"status":row.status,"approved_by_user_id":row.approved_by_user_id,"approved_at":row.approved_at}
    except Exception as exc: db.rollback(); _handle(exc)


@router.post("/communications/templates/baseline/provision")
def provision_baseline_templates(creator_user_id:str,approver_user_id:str,request:Request,db:Session=Depends(get_db)):
    identity=_reviewer(request); svc=CommunicationDeliveryService(db,identity.principal.tenant_id)
    if identity.principal.user_id not in {creator_user_id,approver_user_id}: raise HTTPException(403,"caller must be one of the two human template-governance reviewers")
    try:
        rows=svc.provision_baseline_templates(creator_user_id,approver_user_id); db.commit(); return {"approved_templates":[{"template_id":x.template_id,"locale":x.locale,"channel":x.channel,"version":x.template_version} for x in rows]}
    except Exception as exc: db.rollback(); _handle(exc)


@router.post("/claims/{claim_id}/communications/notices/{notice_id}/queue")
def queue_notice(claim_id:str,notice_id:str,payload:QueueNoticeRequest,request:Request,db:Session=Depends(get_db)):
    identity=_reviewer(request); _authorize_claim_read(db,identity,claim_id); svc=CommunicationDeliveryService(db,identity.principal.tenant_id)
    try:
        rows=svc.queue_released_notice(notice_id,idempotency_key=payload.idempotency_key,trace_id=getattr(identity,"trace_id",None)); db.commit(); return {"dispatches":[svc.dispatch_view(x) for x in rows]}
    except Exception as exc: db.rollback(); _handle(exc)


@router.post("/internal/communications/workers/lease")
def lease_worker(payload:WorkerLeaseRequest,x_communication_worker_token:str|None=Header(default=None),x_tenant_id:str|None=Header(default=None),db:Session=Depends(get_db)):
    _require_worker_token(x_communication_worker_token)
    if not x_tenant_id: raise HTTPException(400,"X-Tenant-Id is required")
    svc=CommunicationDeliveryService(db,x_tenant_id)
    try:
        rows=svc.lease(payload.worker_id,limit=payload.limit); db.commit(); return {"dispatches":[svc.dispatch_view(x) for x in rows]}
    except Exception as exc: db.rollback(); _handle(exc)


@router.post("/internal/communications/dispatches/{dispatch_id}/execute")
def execute_dispatch(dispatch_id:str,payload:WorkerExecuteRequest,x_communication_worker_token:str|None=Header(default=None),x_tenant_id:str|None=Header(default=None),db:Session=Depends(get_db)):
    _require_worker_token(x_communication_worker_token)
    if not x_tenant_id: raise HTTPException(400,"X-Tenant-Id is required")
    svc=CommunicationDeliveryService(db,x_tenant_id)
    try: result=svc.execute(dispatch_id,payload.worker_id); db.commit(); return result
    except Exception as exc: db.rollback(); _handle(exc)


@router.post("/communications/webhooks/{provider_name}")
async def provider_webhook(provider_name:str,request:Request,x_provider_signature:str|None=Header(default=None),db:Session=Depends(get_db)):
    raw=await request.body()
    try: payload=json.loads(raw.decode("utf-8")); parsed=WebhookReceiptRequest.model_validate(payload)
    except Exception as exc: raise HTTPException(400,"invalid provider receipt payload") from exc
    svc=CommunicationDeliveryService(db,parsed.tenant_id)
    if not svc.verify_webhook_signature(raw,x_provider_signature or ""): raise HTTPException(401,"invalid provider webhook signature")
    try:
        row=svc.record_receipt(provider_name,parsed.model_dump(),signature_verified=True); db.commit(); return svc.receipt_view(row)
    except Exception as exc: db.rollback(); _handle(exc)


@router.post("/claims/{claim_id}/communications/notices/{notice_id}/reconcile")
def reconcile(claim_id:str,notice_id:str,payload:ReconcileRequest,request:Request,db:Session=Depends(get_db)):
    identity=_reviewer(request); _authorize_claim_read(db,identity,claim_id); svc=CommunicationDeliveryService(db,identity.principal.tenant_id)
    try:
        row=svc.reconcile_notice(notice_id,idempotency_key=payload.idempotency_key); db.commit(); return {"reconciliation_id":row.reconciliation_id,"status":row.status,"gaps":row.gaps,"reconciliation_sha256":row.reconciliation_sha256}
    except Exception as exc: db.rollback(); _handle(exc)


@router.get("/claims/{claim_id}/communications/notices/{notice_id}.pdf")
def notice_pdf(claim_id:str,notice_id:str,request:Request,locale:str="en",db:Session=Depends(get_db)):
    identity=_identity(request); _authorize_claim_read(db,identity,claim_id); svc=CommunicationDeliveryService(db,identity.principal.tenant_id)
    try:
        data=svc.render_notice_pdf(notice_id,locale=locale); return Response(content=data,media_type="application/pdf",headers={"Content-Disposition":f'inline; filename="{notice_id}.pdf"',"X-Content-SHA256":hashlib.sha256(data).hexdigest()})
    except Exception as exc:_handle(exc)


@router.get("/claims/{claim_id}/communications/audit-export.zip")
def audit_export(claim_id:str,request:Request,db:Session=Depends(get_db)):
    identity=_reviewer(request); _authorize_claim_read(db,identity,claim_id); svc=CommunicationDeliveryService(db,identity.principal.tenant_id)
    try:
        data,digest=svc.build_audit_export(claim_id); return StreamingResponse(iter([data]),media_type="application/zip",headers={"Content-Disposition":f'attachment; filename="{claim_id}-communication-audit.zip"',"X-Content-SHA256":digest})
    except Exception as exc:_handle(exc)


@router.post("/claims/{claim_id}/communications/legal-holds")
def place_hold(claim_id:str,payload:LegalHoldCreateRequest,request:Request,db:Session=Depends(get_db)):
    identity=_reviewer(request); _authorize_claim_read(db,identity,claim_id); svc=CommunicationDeliveryService(db,identity.principal.tenant_id)
    try: row=svc.place_legal_hold(claim_id,identity.principal.user_id,payload.reason); db.commit(); return {"hold_id":row.hold_id,"placed_at":row.placed_at}
    except Exception as exc: db.rollback(); _handle(exc)


@router.post("/claims/{claim_id}/communications/legal-holds/{hold_id}/release")
def release_hold(claim_id:str,hold_id:str,payload:LegalHoldReleaseRequest,request:Request,db:Session=Depends(get_db)):
    identity=_reviewer(request); _authorize_claim_read(db,identity,claim_id); svc=CommunicationDeliveryService(db,identity.principal.tenant_id)
    try: row=svc.release_legal_hold(hold_id,identity.principal.user_id,payload.release_reason); db.commit(); return {"hold_id":row.hold_id,"released_at":row.released_at}
    except Exception as exc: db.rollback(); _handle(exc)


@router.get("/claims/{claim_id}/communications/retention")
def retention(claim_id:str,request:Request,db:Session=Depends(get_db)):
    identity=_reviewer(request); _authorize_claim_read(db,identity,claim_id); return CommunicationDeliveryService(db,identity.principal.tenant_id).retention_status(claim_id)


@router.post("/claims/{claim_id}/communications/dispatches/{dispatch_id}/recover")
def recover(claim_id:str,dispatch_id:str,payload:RecoveryRequest,request:Request,db:Session=Depends(get_db)):
    identity=_reviewer(request); _authorize_claim_read(db,identity,claim_id); svc=CommunicationDeliveryService(db,identity.principal.tenant_id)
    try: row=svc.recover_dispatch(dispatch_id,identity.principal.user_id,payload.reason); db.commit(); return svc.dispatch_view(row)
    except Exception as exc: db.rollback(); _handle(exc)


@router.get("/communications/operations/dashboard")
def dashboard(request:Request,db:Session=Depends(get_db)):
    identity=_reviewer(request); return CommunicationDeliveryService(db,identity.principal.tenant_id).dashboard()


@router.get("/claims/{claim_id}/communications/traceability")
def traceability(claim_id:str,request:Request,db:Session=Depends(get_db)):
    identity=_reviewer(request); _authorize_claim_read(db,identity,claim_id); return CommunicationDeliveryService(db,identity.principal.tenant_id).traceability(claim_id)
