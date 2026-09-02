from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.regulatory_examination_post_commitment_surveillance import post_commitment_surveillance_contract
from app.schemas.regulatory_examination_post_commitment_surveillance import *
from app.services.regulatory_examination_post_commitment_surveillance import RegulatoryExaminationPostCommitmentSurveillanceService

router=APIRouter(tags=["regulatory-examination-post-commitment-surveillance"])
def _identity(r:Request):
    i=getattr(r.state,"identity",None)
    if i is None: raise HTTPException(401,"authenticated identity unavailable")
    return i
def _svc(db,i): return RegulatoryExaminationPostCommitmentSurveillanceService(db,i.principal.tenant_id)

@router.get("/regulatory-examination-post-commitment-surveillance/model")
def model(): return post_commitment_surveillance_contract()
@router.post("/regulatory-examination-post-commitment-surveillance/observations")
def observation(payload:SurveillanceObservationCreate, request:Request, db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).record_observation(i.principal.user_id,payload.model_dump())
@router.post("/regulatory-examination-post-commitment-surveillance/decay-assessment")
def decay(payload:SustainabilityDecayRequest, request:Request, db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).evaluate_decay(payload.model_dump())
@router.post("/regulatory-examination-post-commitment-surveillance/examination-match")
def exam_match(payload:ExaminationMatchRequest, request:Request, db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).match_examination(payload.model_dump())
@router.post("/regulatory-examination-post-commitment-surveillance/cross-entity-recurrence")
def entity_recurrence(payload:CrossEntityRecurrenceRequest, request:Request, db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).propagate_cross_entity(payload.model_dump())
@router.post("/regulatory-examination-post-commitment-surveillance/certification-comparison")
def certification_comparison(payload:CertificationComparisonRequest, request:Request, db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).compare_certification(payload.model_dump())
@router.post("/regulatory-examination-post-commitment-surveillance/investigations")
def investigation(payload:RecurrenceInvestigationCreate, request:Request, db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).open_investigation(i.principal.user_id,payload.model_dump())
@router.post("/regulatory-examination-post-commitment-surveillance/action-plan-links")
def action_plan(payload:RenewedActionPlanLinkRequest, request:Request, db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).link_renewed_action_plan(i.principal.user_id,payload.model_dump())
@router.post("/regulatory-examination-post-commitment-surveillance/reassessments")
def reassess(payload:IndependentReassessmentCreate, request:Request, db:Session=Depends(get_db)):
    i=_identity(request)
    try:return _svc(db,i).record_independent_reassessment(i.principal.user_id,payload.model_dump())
    except PermissionError as e: raise HTTPException(403,str(e)) from e
    except ValueError as e: raise HTTPException(422,str(e)) from e
@router.post("/regulatory-examination-post-commitment-surveillance/{commitment_id}/reopen-decision")
def reopen(commitment_id:str,payload:ReopenDecisionRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request)
    try:return _svc(db,i).decide_reopen(i.principal.user_id,commitment_id,payload.model_dump())
    except PermissionError as e: raise HTTPException(403,str(e)) from e
    except ValueError as e: raise HTTPException(422,str(e)) from e
