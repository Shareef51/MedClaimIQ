from __future__ import annotations
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.api.v1.rag import _identity
from app.core.config import get_settings
from app.db.session import get_db, get_session_factory
from app.domain.access import UserRole
from app.realtime.streaming import PortalClaimRealtimeStreamer
from app.schemas.ingestion import UploadInitiateResponse
from app.schemas.portal import PortalClaimListItem, PortalClaimView, PortalModelResponse, PortalUploadCompleteResponse, PortalUploadInitiateRequest, PortalUploadInitiateResponse, PortalSubmissionView
from app.services.portal import PortalAccessError, PortalService
from app.services.ingestion import IngestionInvariantError

router=APIRouter(tags=["patient-provider-portal"]); settings=get_settings()

def _svc(request:Request,db:Session,tenant_id:str):
    return PortalService(db,tenant_id,storage=request.app.state.object_storage_provider(),bucket_name=settings.s3_bucket,presign_ttl_seconds=settings.upload_presign_ttl_seconds,global_max_file_bytes=settings.upload_max_file_bytes)

def _handle(exc:Exception):
    if isinstance(exc,LookupError): raise HTTPException(404,str(exc)) from exc
    if isinstance(exc,PortalAccessError): raise HTTPException(403,str(exc)) from exc
    if isinstance(exc,IngestionInvariantError): raise HTTPException(422,{"code":exc.code,"message":str(exc)}) from exc
    raise exc

@router.get("/portal-model",response_model=PortalModelResponse)
def portal_model():
    return PortalModelResponse(allowed_roles=("patient","provider","hospital_admin"),visible_sections=("claim status","requested documents","own submission acknowledgements","safe FHIR/provider verification status","SLA/deadline visibility","safe claim timeline"),hidden_internal_sections=("fraud/waste signals","denial-risk reasoning","agent chain-of-thought","critic internals","reviewer notes","GraphRAG contradictions","MCP internals"),upload_rule="requested documents use the existing quarantine-first signed-upload pipeline; no parser/RAG/agent sees them before security acceptance",realtime_rule="external SSE is allowlisted and metadata-minimized; internal agent/guardrail/reviewer event types are never emitted")

@router.get("/portal/claims",response_model=list[PortalClaimListItem])
def claims(request:Request,db:Session=Depends(get_db)):
    identity=_identity(request)
    try:return _svc(request,db,identity.principal.tenant_id).list_claims(identity.principal)
    except Exception as exc:_handle(exc)

@router.get("/portal/claims/{claim_id}",response_model=PortalClaimView)
def claim_view(claim_id:str,request:Request,db:Session=Depends(get_db)):
    identity=_identity(request)
    try:return _svc(request,db,identity.principal.tenant_id).snapshot(identity.principal,claim_id)
    except Exception as exc:_handle(exc)

@router.post("/portal/claims/{claim_id}/requests/{request_id}/uploads",response_model=PortalUploadInitiateResponse,status_code=status.HTTP_201_CREATED)
def initiate(claim_id:str,request_id:str,payload:PortalUploadInitiateRequest,request:Request,idempotency_key:str=Header(alias="Idempotency-Key",min_length=8,max_length=160),trace_id:str|None=Header(default=None,alias="X-Trace-Id"),db:Session=Depends(get_db)):
    identity=_identity(request); svc=_svc(request,db,identity.principal.tenant_id)
    try:
        sub,upload,signed=svc.initiate_request_upload(identity.principal,claim_id,request_id,payload,idempotency_key=idempotency_key,trace_id=trace_id)
        db.commit()
        return PortalUploadInitiateResponse(submission_id=sub.submission_id,acknowledgement_code=sub.acknowledgement_code,upload=UploadInitiateResponse(upload_session_id=upload.upload_session_id,claim_id=upload.claim_id,status=upload.status,method=signed.method,upload_url=signed.url,required_headers=signed.required_headers,form_fields=signed.form_fields,upload_expires_at=upload.upload_expires_at,expected_byte_size=upload.expected_byte_size,media_kind=upload.media_kind))
    except HTTPException: raise
    except Exception as exc: db.rollback(); _handle(exc)

@router.post("/portal/claims/{claim_id}/requests/{request_id}/uploads/{upload_session_id}/complete",response_model=PortalUploadCompleteResponse,status_code=status.HTTP_202_ACCEPTED)
def complete(claim_id:str,request_id:str,upload_session_id:str,request:Request,db:Session=Depends(get_db)):
    identity=_identity(request); svc=_svc(request,db,identity.principal.tenant_id)
    try:
        sub,upload,event=svc.complete_request_upload(identity.principal,claim_id,request_id,upload_session_id,trace_id=getattr(identity,"trace_id",None)); db.commit()
        return PortalUploadCompleteResponse(submission_id=sub.submission_id,acknowledgement_code=sub.acknowledgement_code,status=sub.status,accepted_for_security_processing=upload.status=="uploaded",event_id=event.event_id)
    except Exception as exc: db.rollback(); _handle(exc)

@router.get("/portal/claims/{claim_id}/submissions/{submission_id}",response_model=PortalSubmissionView)
def submission(claim_id:str,submission_id:str,request:Request,db:Session=Depends(get_db)):
    identity=_identity(request); svc=_svc(request,db,identity.principal.tenant_id)
    try:
        row=svc.sync_submission_status(identity.principal,claim_id,submission_id); db.commit(); return row
    except Exception as exc: db.rollback(); _handle(exc)

@router.get("/portal/claims/{claim_id}/events")
def events(claim_id:str,request:Request,after_sequence:int=0,db:Session=Depends(get_db)):
    identity=_identity(request); svc=_svc(request,db,identity.principal.tenant_id)
    try: svc.authorize_claim(identity.principal,claim_id)
    except Exception as exc:_handle(exc)
    streamer=PortalClaimRealtimeStreamer(get_session_factory(),identity.principal.tenant_id,claim_id,after_sequence)
    return StreamingResponse(streamer.events(request.is_disconnected),media_type="text/event-stream",headers={"Cache-Control":"no-cache, no-store","X-Accel-Buffering":"no"})
