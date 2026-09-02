from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.regulatory_examination_reclosed_recovery_surveillance import reclosed_recovery_surveillance_contract
from app.schemas.regulatory_examination_reclosed_recovery_surveillance import *
from app.services.regulatory_examination_reclosed_recovery_surveillance import RegulatoryExaminationReclosedRecoverySurveillanceService
router=APIRouter(tags=["regulatory-examination-reclosed-recovery-surveillance"])
def _identity(r:Request):
    i=getattr(r.state,"identity",None)
    if i is None: raise HTTPException(401,"authenticated identity unavailable")
    return i
def _svc(db,i): return RegulatoryExaminationReclosedRecoverySurveillanceService(db,i.principal.tenant_id)
def _call(fn):
    try: return fn()
    except PermissionError as e: raise HTTPException(403,str(e)) from e
    except ValueError as e: raise HTTPException(422,str(e)) from e
@router.get("/regulatory-examination-reclosed-recovery-surveillance/model")
def model(): return reclosed_recovery_surveillance_contract()
@router.post("/regulatory-examination-reclosed-recovery-surveillance/assessments")
def assess(payload:RecoverySurveillanceAssessment,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).assess_surveillance(payload.model_dump())
@router.post("/regulatory-examination-reclosed-recovery-surveillance/examination-matches")
def match(payload:ExaminationMatchRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).match_examination(payload.model_dump())
@router.post("/regulatory-examination-reclosed-recovery-surveillance/investigations")
def investigation(payload:SustainabilityBreachInvestigationCreate,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _call(lambda:_svc(db,i).create_investigation(i.principal.user_id,payload.model_dump()))
@router.post("/regulatory-examination-reclosed-recovery-surveillance/independent-reassessments")
def reassessment(payload:IndependentReassessmentCreate,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _call(lambda:_svc(db,i).independent_reassess(i.principal.user_id,payload.model_dump()))
@router.post("/regulatory-examination-reclosed-recovery-surveillance/reopening-readiness")
def readiness(payload:ReopeningReadinessRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).readiness(payload.model_dump())
@router.post("/regulatory-examination-reclosed-recovery-surveillance/reopening-decisions")
def reopening(payload:EnterpriseReopeningDecisionCreate,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _call(lambda:_svc(db,i).decide_reopening(i.principal.user_id,payload.model_dump()))
