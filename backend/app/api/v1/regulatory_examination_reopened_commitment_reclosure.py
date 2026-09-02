from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.regulatory_examination_reopened_commitment_reclosure import reopened_commitment_reclosure_contract
from app.schemas.regulatory_examination_reopened_commitment_reclosure import *
from app.services.regulatory_examination_reopened_commitment_reclosure import RegulatoryExaminationReopenedCommitmentReclosureService

router=APIRouter(tags=["regulatory-examination-reopened-commitment-reclosure"])
def _identity(r:Request):
    i=getattr(r.state,"identity",None)
    if i is None: raise HTTPException(401,"authenticated identity unavailable")
    return i
def _svc(db,i): return RegulatoryExaminationReopenedCommitmentReclosureService(db,i.principal.tenant_id)

@router.get("/regulatory-examination-reopened-commitment-reclosure/model")
def model(): return reopened_commitment_reclosure_contract()
@router.post("/regulatory-examination-reopened-commitment-reclosure/plans")
def plans(payload:RenewedRemediationPlanCreate,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).create_renewed_plan(i.principal.user_id,payload.model_dump())
@router.post("/regulatory-examination-reopened-commitment-reclosure/milestones")
def milestones(payload:RenewedMilestoneCreate,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).create_milestone(i.principal.user_id,payload.model_dump())
@router.post("/regulatory-examination-reopened-commitment-reclosure/root-cause-comparison")
def root_causes(payload:RootCauseComparisonRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).compare_root_causes(payload.model_dump())
@router.post("/regulatory-examination-reopened-commitment-reclosure/control-redesign-recommendations")
def redesign(payload:ControlRedesignRecommendationRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).recommend_control_redesign(i.principal.user_id,payload.model_dump())
@router.post("/regulatory-examination-reopened-commitment-reclosure/independent-retests")
def retest(payload:IndependentRetestCreate,request:Request,db:Session=Depends(get_db)):
    i=_identity(request)
    try:return _svc(db,i).independent_retest(i.principal.user_id,payload.model_dump())
    except PermissionError as e: raise HTTPException(403,str(e)) from e
    except ValueError as e: raise HTTPException(422,str(e)) from e
@router.post("/regulatory-examination-reopened-commitment-reclosure/readiness")
def readiness(payload:ReclosureReadinessRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).assess_readiness(payload.model_dump())
@router.post("/regulatory-examination-reopened-commitment-reclosure/second-recurrence")
def second_recurrence(payload:SecondRecurrenceRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).assess_second_recurrence(payload.model_dump())
@router.post("/regulatory-examination-reopened-commitment-reclosure/sustainability-reset")
def sustainability_reset(payload:SustainabilityResetRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).define_sustainability_reset(payload.model_dump())
@router.post("/regulatory-examination-reopened-commitment-reclosure/{commitment_id}/recertify")
def recertify(commitment_id:str,payload:HumanRecertificationRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request)
    try:return _svc(db,i).recertify(i.principal.user_id,commitment_id,payload.model_dump())
    except PermissionError as e: raise HTTPException(403,str(e)) from e
    except ValueError as e: raise HTTPException(422,str(e)) from e
@router.post("/regulatory-examination-reopened-commitment-reclosure/{commitment_id}/reclose")
def reclose(commitment_id:str,payload:ReclosureDecisionRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request)
    try:return _svc(db,i).decide_reclosure(i.principal.user_id,commitment_id,payload.model_dump())
    except PermissionError as e: raise HTTPException(403,str(e)) from e
    except ValueError as e: raise HTTPException(422,str(e)) from e
