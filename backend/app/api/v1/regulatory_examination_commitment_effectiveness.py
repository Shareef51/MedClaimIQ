from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.regulatory_examination_commitment_effectiveness import commitment_effectiveness_contract
from app.schemas.regulatory_examination_commitment_effectiveness import *
from app.services.regulatory_examination_commitment_effectiveness import RegulatoryExaminationCommitmentEffectivenessService
router=APIRouter(tags=["regulatory-examination-commitment-effectiveness"])
def _identity(r:Request):
    i=getattr(r.state,"identity",None)
    if i is None: raise HTTPException(401,"authenticated identity unavailable")
    return i
def _svc(db,i): return RegulatoryExaminationCommitmentEffectivenessService(db,i.principal.tenant_id)
@router.get("/regulatory-examination-commitment-effectiveness/model")
def model(): return commitment_effectiveness_contract()
@router.post("/regulatory-examination-commitment-effectiveness/retests")
def retest(payload:EffectivenessRetestCreate,request:Request,db:Session=Depends(get_db)):
    i=_identity(request)
    try:return _svc(db,i).create_validation(i.principal.user_id,payload.model_dump())
    except PermissionError as e: raise HTTPException(403,str(e)) from e
    except ValueError as e: raise HTTPException(422,str(e)) from e
@router.post("/regulatory-examination-commitment-effectiveness/closure-readiness")
def assess(payload:ClosureAssessmentRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).assess_closure(payload.model_dump())
@router.post("/regulatory-examination-commitment-effectiveness/{commitment_id}/certify-closure")
def certify(commitment_id:str,payload:ClosureCertificationRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request)
    try:return _svc(db,i).certify_closure(i.principal.user_id,commitment_id,payload.model_dump())
    except PermissionError as e: raise HTTPException(403,str(e)) from e
    except ValueError as e: raise HTTPException(422,str(e)) from e
@router.post("/regulatory-examination-commitment-effectiveness/sustainability-observations")
def observation(payload:SustainabilityObservationCreate,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).record_sustainability_observation(i.principal.user_id,payload.model_dump())
@router.post("/regulatory-examination-commitment-effectiveness/sustainability-evaluate")
def sustainability(payload:SustainabilityEvaluationRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).evaluate_sustainability(payload.observations,payload.min_window_days)
@router.post("/regulatory-examination-commitment-effectiveness/recurrence-detect")
def recurrence(payload:RecurrenceDetectionRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).detect_recurrence(payload.commitment,payload.signals)
@router.post("/regulatory-examination-commitment-effectiveness/{commitment_id}/reopen-decision")
def reopen(commitment_id:str,payload:ReopenDecisionRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request)
    try:return _svc(db,i).decide_reopen(i.principal.user_id,commitment_id,payload.model_dump())
    except PermissionError as e: raise HTTPException(403,str(e)) from e
    except ValueError as e: raise HTTPException(422,str(e)) from e
