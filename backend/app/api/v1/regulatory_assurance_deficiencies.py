from fastapi import APIRouter,Depends,HTTPException,Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.regulatory_assurance_deficiencies import regulatory_assurance_deficiency_contract
from app.schemas.regulatory_assurance_deficiencies import *
from app.services.regulatory_assurance_deficiencies import RegulatoryAssuranceDeficiencyService
from app.services.review_workbench import ReviewConflictError,ReviewLockError
router=APIRouter(tags=["regulatory-assurance-deficiencies"])
def _i(r):
    x=getattr(r.state,"identity",None)
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
def _svc(db,t):return RegulatoryAssuranceDeficiencyService(db,t)
@router.get('/regulatory-assurance-deficiencies/model')
def model():return regulatory_assurance_deficiency_contract()
@router.get('/regulatory-assurance-deficiencies/dashboard')
def dashboard(request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:_svc(db,i.principal.tenant_id).dashboard(i.principal.user_id))
@router.post('/regulatory-assurance-deficiencies/exceptions')
def record(payload:AssuranceExceptionRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);x=_run(db,lambda:_svc(db,i.principal.tenant_id).record_exception(i.principal.user_id,**payload.model_dump()));return {"exception_id":x.exception_id,"status":x.status}
@router.post('/regulatory-assurance-deficiencies/aggregate')
def aggregate(payload:AggregateDeficiencyRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);d=_run(db,lambda:_svc(db,i.principal.tenant_id).aggregate(i.principal.user_id,**payload.model_dump()));return {"deficiency_id":d.deficiency_id,"deficiency_key":d.deficiency_key,"version":d.version,"severity":d.severity,"severity_score":d.severity_score}
@router.post('/regulatory-assurance-deficiencies/issues')
def issue(payload:EscalateEnterpriseIssueRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);x=_run(db,lambda:_svc(db,i.principal.tenant_id).propose_issue(i.principal.user_id,**payload.model_dump()));return {"issue_id":x.issue_id,"candidate_material_weakness":x.candidate_material_weakness,"status":x.status}
@router.post('/regulatory-assurance-deficiencies/issues/{issue_id}/escalate')
def escalate(issue_id:str,request:Request,db:Session=Depends(get_db)):
    i=_i(request);x=_run(db,lambda:_svc(db,i.principal.tenant_id).escalate(i.principal.user_id,issue_id));return {"issue_id":x.issue_id,"status":x.status,"escalated_by":x.escalated_by_user_id}
@router.post('/regulatory-assurance-deficiencies/{deficiency_key}/close')
def close(deficiency_key:str,payload:DeficiencyClosureRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);x=_run(db,lambda:_svc(db,i.principal.tenant_id).close_deficiency(i.principal.user_id,deficiency_key,**payload.model_dump()));return {"closure_id":x.closure_id,"version":x.closure_version,"conclusion":x.conclusion,"independent":x.independent}
