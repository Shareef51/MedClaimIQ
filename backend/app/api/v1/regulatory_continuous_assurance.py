from fastapi import APIRouter,Depends,HTTPException,Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.regulatory_continuous_assurance import regulatory_continuous_assurance_contract
from app.schemas.regulatory_continuous_assurance import *
from app.services.regulatory_continuous_assurance import RegulatoryContinuousAssuranceService
from app.services.review_workbench import ReviewConflictError,ReviewLockError
router=APIRouter(tags=["regulatory-continuous-assurance"])
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
def _svc(db,t):return RegulatoryContinuousAssuranceService(db,t)
@router.get('/regulatory-continuous-assurance/model')
def model():return regulatory_continuous_assurance_contract()
@router.get('/regulatory-continuous-assurance/dashboard')
def dashboard(request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:_svc(db,i.principal.tenant_id).dashboard(i.principal.user_id))
@router.post('/regulatory-continuous-assurance/observations')
def observation(payload:AssuranceObservationRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);svc=_svc(db,i.principal.tenant_id);o,d,w=_run(db,lambda:svc.record_observation(i.principal.user_id,**payload.model_dump()));return {"observation_id":o.observation_id,"drift_event_id":d.drift_event_id,"severity":d.severity,"drift_score":d.drift_score,"warning_id":w.warning_id if w else None,"human_investigation_required":bool(w)}
@router.get('/regulatory-continuous-assurance/drift/{drift_event_id}')
def drift(drift_event_id:str,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:_svc(db,i.principal.tenant_id).view_drift(drift_event_id,i.principal.user_id))
@router.post('/regulatory-continuous-assurance/drift/{drift_event_id}/human-investigation')
def investigate(drift_event_id:str,payload:AssuranceInvestigationRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);r=_run(db,lambda:_svc(db,i.principal.tenant_id).investigate(drift_event_id,i.principal.user_id,**payload.model_dump()));return {"investigation_id":r.investigation_id,"sequence":r.review_sequence,"disposition":r.disposition}
