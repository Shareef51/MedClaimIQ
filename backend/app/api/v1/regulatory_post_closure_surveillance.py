from fastapi import APIRouter,Depends,HTTPException,Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.regulatory_post_closure_surveillance import post_closure_surveillance_contract
from app.schemas.regulatory_post_closure_surveillance import *
from app.services.regulatory_post_closure_surveillance import RegulatoryPostClosureSurveillanceService
from app.services.review_workbench import ReviewConflictError,ReviewLockError
router=APIRouter(tags=["regulatory-post-closure-surveillance"])
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
def _svc(db,t): return RegulatoryPostClosureSurveillanceService(db,t)
@router.get('/regulatory-post-closure/model')
def model(): return post_closure_surveillance_contract()
@router.get('/regulatory-post-closure/dashboard')
def dashboard(request:Request,db:Session=Depends(get_db)):
    i=_i(request); return _run(db,lambda:_svc(db,i.principal.tenant_id).dashboard(i.principal.user_id))
@router.post('/regulatory-post-closure/signals')
def signal(payload:SurveillanceSignalRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request); x=_run(db,lambda:_svc(db,i.principal.tenant_id).record_signal(i.principal.user_id,**payload.model_dump())); return {"signal_id":x.signal_id,"status":x.status}
@router.post('/regulatory-post-closure/reopen-candidates')
def candidate(payload:ReopenCandidateRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request); x=_run(db,lambda:_svc(db,i.principal.tenant_id).create_candidate(i.principal.user_id,**payload.model_dump())); return {"candidate_id":x.candidate_id,"version":x.version,"status":x.status,"human_decision_required":x.human_decision_required}
@router.post('/regulatory-post-closure/reopen-candidates/{candidate_id}/decision')
def decide(candidate_id:str,payload:HumanReopenDecisionRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request); x=_run(db,lambda:_svc(db,i.principal.tenant_id).decide_reopen(i.principal.user_id,candidate_id,**payload.model_dump())); return {"investigation_id":x.investigation_id,"decision":x.decision,"revalidation_required":x.revalidation_required}
