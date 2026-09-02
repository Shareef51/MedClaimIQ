from fastapi import APIRouter,Depends,HTTPException,Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.regulatory_submission_transport import regulatory_submission_transport_contract
from app.schemas.regulatory_submission_transport import *
from app.services.regulatory_submission_transport import RegulatorySubmissionTransportService
from app.services.review_workbench import ReviewConflictError,ReviewLockError
router=APIRouter(tags=["regulatory-submission-transport"])
def _i(request):
    x=getattr(request.state,"identity",None)
    if x is None:raise HTTPException(401,"authenticated identity unavailable")
    return x
def _run(db,fn):
    try:r=fn();db.commit();return r
    except Exception as e:
        db.rollback()
        if isinstance(e,LookupError):raise HTTPException(404,str(e)) from e
        if isinstance(e,(ReviewConflictError,ReviewLockError)):raise HTTPException(409,str(e)) from e
        if isinstance(e,(ValueError,PermissionError)):raise HTTPException(400,str(e)) from e
        raise
@router.get("/regulatory-transport-model")
def model():return regulatory_submission_transport_contract()
@router.get("/regulatory-transport/dashboard")
def dashboard(request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:RegulatorySubmissionTransportService(db,i.principal.tenant_id).dashboard(i.principal.user_id))
@router.post("/regulatory-transport/destinations")
def destination(payload:DestinationCreateRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);r=_run(db,lambda:RegulatorySubmissionTransportService(db,i.principal.tenant_id).create_destination(i.principal.user_id,**payload.model_dump()));return {"destination_id":r.destination_id,"destination_key":r.destination_key,"regulator_name":r.regulator_name,"schema_name":r.schema_name,"schema_version":r.schema_version,"active":r.active}
@router.post("/regulatory-transport/packages/{package_id}/release")
def release(package_id:str,payload:SubmissionReleaseRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);r=_run(db,lambda:RegulatorySubmissionTransportService(db,i.principal.tenant_id).release(package_id,i.principal.user_id,**payload.model_dump()));return {"release_id":r.release_id,"release_sha256":r.release_sha256,"released_by_user_id":r.released_by_user_id,"released_at":r.released_at}
@router.post("/regulatory-transport/transmissions/{transmission_id}/recover")
def recover(transmission_id:str,payload:RecoveryRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);r=_run(db,lambda:RegulatorySubmissionTransportService(db,i.principal.tenant_id).recover(transmission_id,i.principal.user_id,rationale=payload.rationale));return {"transmission_id":r.transmission_id,"status":r.status,"next_attempt_at":r.next_attempt_at}
@router.post("/regulatory/webhooks/acknowledgments")
def acknowledgment(payload:AckRequest,request:Request,db:Session=Depends(get_db)):
    # In production the public provider route has a dedicated HMAC boundary; identity is deliberately not used as authorization.
    tenant=request.headers.get("X-Tenant-Id","").strip() or getattr(request.state,"tenant_id",None)
    if not tenant:raise HTTPException(400,"X-Tenant-Id is required for signed regulator acknowledgment")
    r=_run(db,lambda:RegulatorySubmissionTransportService(db,tenant).acknowledgment(**payload.model_dump()));return {"acknowledgment_id":r.acknowledgment_id,"acknowledgment_status":r.acknowledgment_status,"signature_verified":r.signature_verified,"receipt_sha256":r.receipt_sha256}
@router.get("/regulatory-transport/transmissions/{transmission_id}/traceability")
def trace(transmission_id:str,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:RegulatorySubmissionTransportService(db,i.principal.tenant_id).traceability(transmission_id,i.principal.user_id))
