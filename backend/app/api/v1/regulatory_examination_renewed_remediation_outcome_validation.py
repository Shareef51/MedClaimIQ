from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.regulatory_examination_renewed_remediation_outcome_validation import renewed_remediation_outcome_validation_contract
from app.schemas.regulatory_examination_renewed_remediation_outcome_validation import *
from app.services.regulatory_examination_renewed_remediation_outcome_validation import RegulatoryExaminationRenewedRemediationOutcomeValidationService
router=APIRouter(tags=["regulatory-examination-renewed-remediation-outcome-validation"])
def _identity(r:Request):
    i=getattr(r.state,"identity",None)
    if i is None: raise HTTPException(401,"authenticated identity unavailable")
    return i
def _svc(db,i): return RegulatoryExaminationRenewedRemediationOutcomeValidationService(db,i.principal.tenant_id)
def _call(fn):
    try: return fn()
    except PermissionError as e: raise HTTPException(403,str(e)) from e
    except ValueError as e: raise HTTPException(422,str(e)) from e
@router.get("/regulatory-examination-renewed-remediation-outcome-validation/model")
def model(): return renewed_remediation_outcome_validation_contract()
@router.post("/regulatory-examination-renewed-remediation-outcome-validation/outcomes")
def outcomes(payload:RecoveryOutcomeRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).measure_outcome(payload.model_dump())
@router.post("/regulatory-examination-renewed-remediation-outcome-validation/independent-validations")
def validation(payload:IndependentRecoveryValidationCreate,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _call(lambda:_svc(db,i).independent_validate(i.principal.user_id,payload.model_dump()))
@router.post("/regulatory-examination-renewed-remediation-outcome-validation/residual-risk-acceptance")
def risk(payload:ResidualRiskAcceptanceCreate,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _call(lambda:_svc(db,i).accept_residual_risk(i.principal.user_id,payload.model_dump()))
@router.post("/regulatory-examination-renewed-remediation-outcome-validation/sustainability-observations")
def observation(payload:SustainabilityObservationCreate,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).observe_sustainability(i.principal.user_id,payload.model_dump())
@router.post("/regulatory-examination-renewed-remediation-outcome-validation/reclosure-readiness")
def readiness(payload:ReclosureReadinessRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).readiness(payload.model_dump())
@router.post("/regulatory-examination-renewed-remediation-outcome-validation/recovery-certifications")
def certification(payload:ExecutiveRecoveryCertificationCreate,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _call(lambda:_svc(db,i).certify_recovery(i.principal.user_id,payload.model_dump()))
@router.post("/regulatory-examination-renewed-remediation-outcome-validation/reclosure-decisions")
def reclosure(payload:ExecutiveReclosureDecisionCreate,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _call(lambda:_svc(db,i).reclose(i.principal.user_id,payload.model_dump()))
