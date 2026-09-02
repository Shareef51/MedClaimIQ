from fastapi import APIRouter,Depends,HTTPException,Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.regulatory_deficiency_lifecycle import regulatory_deficiency_lifecycle_contract
from app.schemas.regulatory_deficiency_lifecycle import *
from app.services.regulatory_deficiency_lifecycle import RegulatoryDeficiencyLifecycleService
from app.services.review_workbench import ReviewConflictError,ReviewLockError
router=APIRouter(tags=["regulatory-deficiency-lifecycle"])
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
def _svc(db,t): return RegulatoryDeficiencyLifecycleService(db,t)
@router.get('/regulatory-deficiency-lifecycle/model')
def model(): return regulatory_deficiency_lifecycle_contract()
@router.get('/regulatory-deficiency-lifecycle/dashboard')
def dashboard(request:Request,db:Session=Depends(get_db)):
    i=_i(request); return _run(db,lambda:_svc(db,i.principal.tenant_id).dashboard(i.principal.user_id))
@router.post('/regulatory-deficiency-lifecycle/investigations')
def investigate(payload:InvestigationRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request); x=_run(db,lambda:_svc(db,i.principal.tenant_id).investigate(i.principal.user_id,**payload.model_dump())); return {"investigation_id":x.investigation_id,"status":x.status}
@router.post('/regulatory-deficiency-lifecycle/{deficiency_key}/dispositions')
def disposition(deficiency_key:str,payload:DispositionRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request); x=_run(db,lambda:_svc(db,i.principal.tenant_id).disposition(i.principal.user_id,deficiency_key,**payload.model_dump())); return {"disposition_id":x.disposition_id,"version":x.version,"classification":x.classification}
@router.post('/regulatory-deficiency-lifecycle/corrective-actions')
def plan(payload:CorrectiveActionPlanRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request); x=_run(db,lambda:_svc(db,i.principal.tenant_id).create_plan(i.principal.user_id,**payload.model_dump())); return {"plan_id":x.plan_id,"status":x.status}
@router.post('/regulatory-deficiency-lifecycle/corrective-actions/{plan_id}/approve')
def approve(plan_id:str,request:Request,db:Session=Depends(get_db)):
    i=_i(request); x=_run(db,lambda:_svc(db,i.principal.tenant_id).approve_plan(i.principal.user_id,plan_id)); return {"plan_id":x.plan_id,"status":x.status,"approved_by":x.approved_by_user_id}
@router.post('/regulatory-deficiency-lifecycle/{deficiency_key}/executive-attestations')
def attest(deficiency_key:str,payload:ExecutiveAttestationRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request); x=_run(db,lambda:_svc(db,i.principal.tenant_id).attest(i.principal.user_id,deficiency_key,**payload.model_dump())); return {"attestation_id":x.attestation_id,"version":x.version,"conclusion":x.conclusion,"human_attestation":x.human_attestation}
