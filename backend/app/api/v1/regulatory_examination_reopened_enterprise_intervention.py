from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.regulatory_examination_reopened_enterprise_intervention import reopened_enterprise_intervention_contract
from app.schemas.regulatory_examination_reopened_enterprise_intervention import *
from app.services.regulatory_examination_reopened_enterprise_intervention import RegulatoryExaminationReopenedEnterpriseInterventionService

router=APIRouter(tags=["regulatory-examination-reopened-enterprise-intervention"])
def _identity(r:Request):
    i=getattr(r.state,"identity",None)
    if i is None: raise HTTPException(401,"authenticated identity unavailable")
    return i
def _svc(db,i): return RegulatoryExaminationReopenedEnterpriseInterventionService(db,i.principal.tenant_id)
def _call(fn):
    try: return fn()
    except PermissionError as e: raise HTTPException(403,str(e)) from e
    except ValueError as e: raise HTTPException(422,str(e)) from e

@router.get("/regulatory-examination-reopened-enterprise-intervention/model")
def model(): return reopened_enterprise_intervention_contract()
@router.post("/regulatory-examination-reopened-enterprise-intervention/plans")
def plan(payload:ReopenedInterventionPlanCreate,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).create_plan(i.principal.user_id,payload.model_dump())
@router.post("/regulatory-examination-reopened-enterprise-intervention/actions")
def action(payload:RenewedSystemicActionCreate,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).create_action(i.principal.user_id,payload.model_dump())
@router.post("/regulatory-examination-reopened-enterprise-intervention/root-cause-comparison")
def roots(payload:RootCauseComparisonRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).compare_root_causes(payload.model_dump())
@router.post("/regulatory-examination-reopened-enterprise-intervention/propagation-readiness")
def propagation(payload:PropagationReadinessRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).propagation_readiness(payload.model_dump())
@router.post("/regulatory-examination-reopened-enterprise-intervention/control-redesign")
def redesign(payload:ControlRedesignRecommendationRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).control_redesign_recommendation(payload.model_dump())
@router.post("/regulatory-examination-reopened-enterprise-intervention/independent-revalidation")
def revalidation(payload:IndependentRevalidationRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _call(lambda:_svc(db,i).independent_revalidation(i.principal.user_id,payload.model_dump()))
@router.post("/regulatory-examination-reopened-enterprise-intervention/second-systemic-recurrence")
def recurrence(payload:SecondSystemicRecurrenceRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).second_recurrence(payload.model_dump())
@router.post("/regulatory-examination-reopened-enterprise-intervention/sustainability-reset")
def reset(payload:SustainabilityResetRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).sustainability_reset(payload.model_dump())
@router.post("/regulatory-examination-reopened-enterprise-intervention/residual-risk-reassessment")
def risk(payload:ResidualRiskReassessmentRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _call(lambda:_svc(db,i).residual_risk_reassessment(i.principal.user_id,payload.model_dump()))
@router.post("/regulatory-examination-reopened-enterprise-intervention/reclosure-readiness")
def readiness(payload:ReclosureReadinessRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).reclosure_readiness(payload.model_dump())
@router.post("/regulatory-examination-reopened-enterprise-intervention/executive-recertification")
def recert(payload:ExecutiveRecertificationRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _call(lambda:_svc(db,i).executive_recertification(i.principal.user_id,payload.model_dump()))
@router.post("/regulatory-examination-reopened-enterprise-intervention/reclosure")
def reclose(payload:ProgramReclosureRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _call(lambda:_svc(db,i).reclose_program(i.principal.user_id,payload.model_dump()))
