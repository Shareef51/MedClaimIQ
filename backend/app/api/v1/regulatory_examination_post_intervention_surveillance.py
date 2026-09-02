from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.regulatory_examination_post_intervention_surveillance import post_intervention_surveillance_contract
from app.schemas.regulatory_examination_post_intervention_surveillance import *
from app.services.regulatory_examination_post_intervention_surveillance import RegulatoryExaminationPostInterventionSurveillanceService

router=APIRouter(tags=["regulatory-examination-post-intervention-surveillance"])
def _identity(r:Request):
    i=getattr(r.state,"identity",None)
    if i is None: raise HTTPException(401,"authenticated identity unavailable")
    return i
def _svc(db,i): return RegulatoryExaminationPostInterventionSurveillanceService(db,i.principal.tenant_id)

@router.get("/regulatory-examination-post-intervention-surveillance/model")
def model(): return post_intervention_surveillance_contract()
@router.post("/regulatory-examination-post-intervention-surveillance/signal")
def signal(payload:SurveillanceSignalRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).surveillance_signal(payload.model_dump())
@router.post("/regulatory-examination-post-intervention-surveillance/examination-correlation")
def correlate(payload:ExaminationCorrelationRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).correlate_examination(payload.model_dump())
@router.post("/regulatory-examination-post-intervention-surveillance/investigations")
def investigate(payload:RecurrenceInvestigationRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).open_investigation(i.principal.user_id,payload.model_dump())
@router.post("/regulatory-examination-post-intervention-surveillance/independent-reassessment")
def reassess(payload:IndependentReassessmentRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request)
    try: return _svc(db,i).independent_reassessment(i.principal.user_id,payload.model_dump())
    except PermissionError as e: raise HTTPException(403,str(e)) from e
@router.post("/regulatory-examination-post-intervention-surveillance/reopening-readiness")
def readiness(payload:ReopeningReadinessRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).reopening_readiness(payload.model_dump())
@router.post("/regulatory-examination-post-intervention-surveillance/reopening-decision")
def reopening(payload:ProgramReopeningDecisionRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request)
    try: return _svc(db,i).reopening_decision(i.principal.user_id,payload.model_dump())
    except (PermissionError,ValueError) as e: raise HTTPException(403 if isinstance(e,PermissionError) else 422,str(e)) from e
