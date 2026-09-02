from fastapi import APIRouter,Depends,HTTPException,Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.recovery_control_assurance import recovery_control_assurance_contract
from app.schemas.recovery_control_assurance import *
from app.services.recovery_control_assurance import RecoveryControlAssuranceService
from app.services.review_workbench import ReviewConflictError,ReviewLockError
router=APIRouter(tags=["recovery-control-assurance"])
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
@router.get("/recovery-control-assurance-model")
def model():return recovery_control_assurance_contract()
@router.get("/recovery-control-assurance/dashboard")
def dashboard(request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:RecoveryControlAssuranceService(db,i.principal.tenant_id).dashboard(i.principal.user_id))
@router.post("/recovery-control-assurance/reporting-periods")
def create_period(payload:ReportingPeriodCreateRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:RecoveryControlAssuranceService(db,i.principal.tenant_id).create_reporting_period(i.principal.user_id,**payload.model_dump()))
@router.get("/recovery-control-assurance/reporting-periods/{period_id}")
def workbench(period_id:str,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:RecoveryControlAssuranceService(db,i.principal.tenant_id).workbench(period_id,i.principal.user_id))
@router.post("/recovery-control-assurance/reporting-periods/{period_id}/attestations")
def attest(period_id:str,request:Request,db:Session=Depends(get_db)):
    i=_i(request);svc=RecoveryControlAssuranceService(db,i.principal.tenant_id);return _run(db,lambda:svc._attestation_view(svc.prepare_attestation(period_id,i.principal.user_id)))
@router.post("/recovery-control-assurance/reporting-periods/{period_id}/packages")
def create_package(period_id:str,payload:SubmissionPackageCreateRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);svc=RecoveryControlAssuranceService(db,i.principal.tenant_id);return _run(db,lambda:svc._package_view(svc.create_package(period_id,i.principal.user_id,**payload.model_dump())))
@router.post("/recovery-control-assurance/packages/{package_id}/lock")
def lock_package(package_id:str,payload:PackageLockRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);svc=RecoveryControlAssuranceService(db,i.principal.tenant_id);return _run(db,lambda:svc._package_view(svc.lock_package(package_id,i.principal.user_id,**payload.model_dump())))
@router.post("/recovery-control-assurance/packages/{package_id}/certify")
def certify(package_id:str,payload:CertificationRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);svc=RecoveryControlAssuranceService(db,i.principal.tenant_id);r=_run(db,lambda:svc.certify_package(package_id,i.principal.user_id,rationale=payload.rationale));return {"certification_id":r.certification_id,"certification_sequence":r.certification_sequence,"certification_sha256":r.certification_sha256,"previous_certification_sha256":r.previous_certification_sha256,"maker_user_id":r.maker_user_id,"checker_user_id":r.checker_user_id,"certified_at":r.certified_at}
@router.post("/recovery-control-assurance/packages/{package_id}/stage")
def stage(package_id:str,payload:SubmissionStageRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);svc=RecoveryControlAssuranceService(db,i.principal.tenant_id);return _run(db,lambda:svc._package_view(svc.stage_submission(package_id,i.principal.user_id,rationale=payload.rationale)))
@router.post("/recovery-control-assurance/packages/{package_id}/receipt")
def receipt(package_id:str,payload:SubmissionReceiptRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);r=_run(db,lambda:RecoveryControlAssuranceService(db,i.principal.tenant_id).record_submission_receipt(package_id,i.principal.user_id,**payload.model_dump()));return {"receipt_id":r.receipt_id,"external_submission_id":r.external_submission_id,"submission_status":r.submission_status,"payload_sha256":r.payload_sha256,"received_at":r.received_at}
@router.post("/recovery-control-assurance/packages/{package_id}/annotations")
def annotate(package_id:str,payload:AuditAnnotationRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);r=_run(db,lambda:RecoveryControlAssuranceService(db,i.principal.tenant_id).add_annotation(package_id,i.principal.user_id,**payload.model_dump()));return {"annotation_id":r.annotation_id,"body_sha256":r.body_sha256,"created_at":r.created_at}
@router.get("/recovery-control-assurance/packages/{package_id}/traceability")
def trace(package_id:str,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:RecoveryControlAssuranceService(db,i.principal.tenant_id).traceability(package_id,i.principal.user_id))
