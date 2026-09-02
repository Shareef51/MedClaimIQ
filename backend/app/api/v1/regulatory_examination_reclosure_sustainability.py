from fastapi import APIRouter,Depends,HTTPException,Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.regulatory_examination_reclosure_sustainability import reclosure_sustainability_contract
from app.schemas.regulatory_examination_reclosure_sustainability import *
from app.services.regulatory_examination_reclosure_sustainability import RegulatoryExaminationReclosureSustainabilityService
router=APIRouter(tags=["regulatory-examination-reclosure-sustainability"])
def _identity(r:Request):
    i=getattr(r.state,"identity",None)
    if i is None: raise HTTPException(401,"authenticated identity unavailable")
    return i
def _svc(db,i): return RegulatoryExaminationReclosureSustainabilityService(db,i.principal.tenant_id)
@router.get("/regulatory-examination-reclosure-sustainability/model")
def model(): return reclosure_sustainability_contract()
@router.post("/regulatory-examination-reclosure-sustainability/observations")
def observation(payload:SustainabilityObservationCreate,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).record_observation(i.principal.user_id,payload.model_dump())
@router.post("/regulatory-examination-reclosure-sustainability/repeat-recurrence")
def recurrence(payload:RepeatRecurrenceRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).assess_recurrence(payload.model_dump())
@router.post("/regulatory-examination-reclosure-sustainability/reclosure-comparison")
def comparison(payload:ReclosureComparisonRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).compare_reclosures(payload.model_dump())
@router.post("/regulatory-examination-reclosure-sustainability/escalations")
def escalation(payload:EscalationAssessmentRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).create_escalation(i.principal.user_id,payload.model_dump())
@router.post("/regulatory-examination-reclosure-sustainability/investigations")
def investigation(payload:HumanInvestigationCreate,request:Request,db:Session=Depends(get_db)):
    i=_identity(request)
    try:return _svc(db,i).open_investigation(i.principal.user_id,payload.model_dump())
    except PermissionError as e: raise HTTPException(403,str(e)) from e
@router.post("/regulatory-examination-reclosure-sustainability/governance-actions")
def action(payload:GovernanceActionCreate,request:Request,db:Session=Depends(get_db)):
    i=_identity(request)
    try:return _svc(db,i).create_governance_action(i.principal.user_id,payload.model_dump())
    except PermissionError as e: raise HTTPException(403,str(e)) from e
