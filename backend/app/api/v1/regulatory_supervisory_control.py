from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.regulatory_supervisory_control import regulatory_supervisory_control_contract
from app.schemas.regulatory_supervisory_control import *
from app.services.regulatory_supervisory_control import RegulatorySupervisoryControlService
from app.services.review_workbench import ReviewConflictError, ReviewLockError
router=APIRouter(tags=["regulatory-supervisory-control"])

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

@router.get("/regulatory-supervision-model")
def model():return regulatory_supervisory_control_contract()
@router.get("/regulatory-supervision/dashboard")
def dashboard(request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:RegulatorySupervisoryControlService(db,i.principal.tenant_id).dashboard(i.principal.user_id))
@router.post("/regulatory-supervision/cases/refresh")
def refresh(payload:CaseRefreshRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);svc=RegulatorySupervisoryControlService(db,i.principal.tenant_id);svc._reader(i.principal.user_id);return _run(db,lambda:svc.refresh_cases(transmission_id=payload.transmission_id,actor_id=i.principal.user_id,actor_type="human_supervisory_refresh"))
@router.post("/regulatory-supervision/cases/{case_id}/rejection-root-cause")
def rejection(case_id:str,payload:RejectionRootCauseRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);r=_run(db,lambda:RegulatorySupervisoryControlService(db,i.principal.tenant_id).classify_rejection(case_id,i.principal.user_id,**payload.model_dump()));return {"case_id":r.case_id,"rejection_root_cause":r.rejection_root_cause,"case_version":r.case_version}
@router.post("/regulatory-supervision/cases/{case_id}/amendment-effectiveness")
def amendment(case_id:str,payload:AmendmentEffectivenessRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);r=_run(db,lambda:RegulatorySupervisoryControlService(db,i.principal.tenant_id).record_amendment_effectiveness(case_id,i.principal.user_id,**payload.model_dump()));return {"case_id":r.case_id,"amendment_effectiveness":r.amendment_effectiveness,"case_version":r.case_version}
@router.post("/regulatory-supervision/cases/{case_id}/attestations")
def attestation(case_id:str,payload:AttestationPrepareRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);r=_run(db,lambda:RegulatorySupervisoryControlService(db,i.principal.tenant_id).prepare_attestation(case_id,i.principal.user_id,**payload.model_dump()));return {"attestation_id":r.attestation_id,"attestation_version":r.attestation_version,"control_effectiveness_pct":r.control_effectiveness_pct,"material_blockers":r.material_blockers,"payload_sha256":r.payload_sha256}
@router.post("/regulatory-supervision/cases/{case_id}/attestations/{attestation_id}/certify")
def certify(case_id:str,attestation_id:str,payload:CertificationRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);r=_run(db,lambda:RegulatorySupervisoryControlService(db,i.principal.tenant_id).certify(case_id,attestation_id,i.principal.user_id,**payload.model_dump()));return {"certification_id":r.certification_id,"certification_sequence":r.certification_sequence,"supervisor_user_id":r.supervisor_user_id,"certification_sha256":r.certification_sha256}
@router.post("/regulatory-supervision/exceptions/{exception_id}/resolve")
def resolve_exception(exception_id:str,payload:ExceptionResolutionRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);r=_run(db,lambda:RegulatorySupervisoryControlService(db,i.principal.tenant_id).resolve_exception(exception_id,i.principal.user_id,**payload.model_dump()));return {"exception_id":r.exception_id,"status":r.status}
@router.post("/regulatory-supervision/cases/{case_id}/annotations")
def annotate(case_id:str,payload:AnnotationRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);r=_run(db,lambda:RegulatorySupervisoryControlService(db,i.principal.tenant_id).annotate(case_id,i.principal.user_id,**payload.model_dump()));return {"annotation_id":r.annotation_id,"body_sha256":r.body_sha256}
@router.post("/regulatory-supervision/cases/{case_id}/correspondence")
def correspondence(case_id:str,payload:CorrespondenceRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);r=_run(db,lambda:RegulatorySupervisoryControlService(db,i.principal.tenant_id).correspondence(case_id,i.principal.user_id,**payload.model_dump()));return {"correspondence_id":r.correspondence_id,"payload_sha256":r.payload_sha256}
@router.post("/regulatory-supervision/calendar/deadlines")
def deadline(payload:CalendarDeadlineRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);r=_run(db,lambda:RegulatorySupervisoryControlService(db,i.principal.tenant_id).create_deadline(i.principal.user_id,**payload.model_dump()));return {"deadline_id":r.deadline_id,"due_date":r.due_date,"status":r.status}
@router.get("/regulatory-supervision/cases/{case_id}/traceability")
def trace(case_id:str,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:RegulatorySupervisoryControlService(db,i.principal.tenant_id).traceability(case_id,i.principal.user_id))
@router.get("/regulatory-supervision/cases/{case_id}/audit-export")
def export(case_id:str,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:RegulatorySupervisoryControlService(db,i.principal.tenant_id).audit_export(case_id,i.principal.user_id))
