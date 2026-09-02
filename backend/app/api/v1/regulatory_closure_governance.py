from fastapi import APIRouter,Depends,HTTPException,Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.regulatory_closure_governance import regulatory_closure_governance_contract
from app.schemas.regulatory_closure_governance import *
from app.services.regulatory_closure_governance import RegulatoryClosureGovernanceService
from app.services.review_workbench import ReviewConflictError,ReviewLockError
router=APIRouter(tags=["regulatory-closure-governance"])
def _i(r):
    x=getattr(r.state,"identity",None)
    if x is None: raise HTTPException(401,"authenticated identity unavailable")
    return x
def _run(db,fn):
    try: r=fn(); db.commit(); return r
    except Exception as e:
        db.rollback()
        if isinstance(e,LookupError): raise HTTPException(404,str(e)) from e
        if isinstance(e,(ReviewConflictError,ReviewLockError)): raise HTTPException(409,str(e)) from e
        if isinstance(e,(ValueError,PermissionError)): raise HTTPException(400,str(e)) from e
        raise
def _svc(db,t): return RegulatoryClosureGovernanceService(db,t)
@router.get('/regulatory-closure-governance/model')
def model(): return regulatory_closure_governance_contract()
@router.get('/regulatory-closure-governance/dashboard')
def dashboard(request:Request,db:Session=Depends(get_db)):
    i=_i(request); return _run(db,lambda:_svc(db,i.principal.tenant_id).dashboard(i.principal.user_id))
@router.post('/regulatory-closure-governance/packages')
def create_package(payload:ClosurePackageRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request); x=_run(db,lambda:_svc(db,i.principal.tenant_id).create_package(i.principal.user_id,**payload.model_dump())); return {"package_id":x.package_id,"status":x.status,"readiness_score":x.readiness_score}
@router.post('/regulatory-closure-governance/packages/{package_id}/certify')
def certify(package_id:str,payload:CertificationRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request); x=_run(db,lambda:_svc(db,i.principal.tenant_id).certify(i.principal.user_id,package_id,**payload.model_dump())); return {"certification_id":x.certification_id,"version":x.version,"conclusion":x.conclusion,"human_certification":x.human_certification}
@router.post('/regulatory-closure-governance/sustainability')
def sustainability(payload:SustainabilityWindowRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request); x=_run(db,lambda:_svc(db,i.principal.tenant_id).start_sustainability(i.principal.user_id,**payload.model_dump())); return {"window_id":x.window_id,"status":x.status}
@router.post('/regulatory-closure-governance/sustainability/{window_id}/observations')
def observe(window_id:str,payload:SustainabilityObservationRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request); x=_run(db,lambda:_svc(db,i.principal.tenant_id).observe(i.principal.user_id,window_id,**payload.model_dump())); return {"window_id":x.window_id,"status":x.status,"observed_passes":x.observed_passes,"recurrence_detected":x.recurrence_detected}
@router.post('/regulatory-closure-governance/{deficiency_key}/reopen-decisions')
def reopen(deficiency_key:str,payload:ReopenDecisionRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request); x=_run(db,lambda:_svc(db,i.principal.tenant_id).reopen_decision(i.principal.user_id,deficiency_key,**payload.model_dump())); return {"decision_id":x.decision_id,"decision":x.decision}
