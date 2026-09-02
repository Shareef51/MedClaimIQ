from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.regulatory_examination_enterprise_intervention_sustainability import enterprise_intervention_sustainability_contract
from app.schemas.regulatory_examination_enterprise_intervention_sustainability import *
from app.services.regulatory_examination_enterprise_intervention_sustainability import RegulatoryExaminationEnterpriseInterventionSustainabilityService

router=APIRouter(tags=["regulatory-examination-enterprise-intervention-sustainability"])
def _identity(r:Request):
    i=getattr(r.state,"identity",None)
    if i is None: raise HTTPException(401,"authenticated identity unavailable")
    return i
def _svc(db,i): return RegulatoryExaminationEnterpriseInterventionSustainabilityService(db,i.principal.tenant_id)

@router.get("/regulatory-examination-enterprise-intervention-sustainability/model")
def model(): return enterprise_intervention_sustainability_contract()
@router.post("/regulatory-examination-enterprise-intervention-sustainability/risk-reduction")
def risk_reduction(payload:RiskReductionAssessmentRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).risk_reduction(payload.model_dump())
@router.post("/regulatory-examination-enterprise-intervention-sustainability/independent-assurance")
def assurance(payload:SustainabilityAssuranceRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request)
    try: return _svc(db,i).sustainability_assurance(i.principal.user_id,payload.model_dump())
    except PermissionError as e: raise HTTPException(403,str(e)) from e
@router.post("/regulatory-examination-enterprise-intervention-sustainability/residual-risk-acceptance")
def residual_risk(payload:ResidualRiskAcceptanceRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request)
    try: return _svc(db,i).accept_residual_risk(i.principal.user_id,payload.model_dump())
    except (PermissionError,ValueError) as e: raise HTTPException(403 if isinstance(e,PermissionError) else 422,str(e)) from e
@router.post("/regulatory-examination-enterprise-intervention-sustainability/closure-readiness")
def readiness(payload:ClosureReadinessRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).closure_readiness(payload.model_dump())
@router.post("/regulatory-examination-enterprise-intervention-sustainability/executive-closure")
def closure(payload:ExecutiveProgramClosureRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request)
    try: return _svc(db,i).executive_closure(i.principal.user_id,payload.model_dump())
    except (PermissionError,ValueError) as e: raise HTTPException(403 if isinstance(e,PermissionError) else 422,str(e)) from e
@router.post("/regulatory-examination-enterprise-intervention-sustainability/recurrence-signal")
def recurrence(payload:RecurrenceReopenSignalRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).recurrence_signal(payload.model_dump())
