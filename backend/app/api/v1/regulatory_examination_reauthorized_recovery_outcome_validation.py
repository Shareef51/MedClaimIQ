from fastapi import APIRouter,Depends,HTTPException,Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.regulatory_examination_reauthorized_recovery_outcome_validation import reauthorized_recovery_outcome_contract
from app.schemas.regulatory_examination_reauthorized_recovery_outcome_validation import *
from app.services.regulatory_examination_reauthorized_recovery_outcome_validation import RegulatoryExaminationReauthorizedRecoveryOutcomeValidationService
router=APIRouter(tags=["regulatory-examination-reauthorized-recovery-outcome-validation"])
def _identity(r:Request):
    i=getattr(r.state,"identity",None)
    if i is None: raise HTTPException(401,"authenticated identity unavailable")
    return i
def _svc(db,i): return RegulatoryExaminationReauthorizedRecoveryOutcomeValidationService(db,i.principal.tenant_id)
def _call(fn):
    try:return fn()
    except PermissionError as e: raise HTTPException(403,str(e)) from e
    except ValueError as e: raise HTTPException(422,str(e)) from e
@router.get("/regulatory-examination-reauthorized-recovery-outcome-validation/model")
def model(): return reauthorized_recovery_outcome_contract()
@router.post("/regulatory-examination-reauthorized-recovery-outcome-validation/outcomes")
def outcomes(payload:ReauthorizedRecoveryOutcomeRequest,request:Request,db:Session=Depends(get_db)): i=_identity(request); return _svc(db,i).outcomes(payload.model_dump())
@router.post("/regulatory-examination-reauthorized-recovery-outcome-validation/systemic-risk-reduction")
def risk(payload:ReauthorizedSystemicRiskReductionRequest,request:Request,db:Session=Depends(get_db)): i=_identity(request); return _svc(db,i).risk_reduction(payload.model_dump())
@router.post("/regulatory-examination-reauthorized-recovery-outcome-validation/cross-entity-completion")
def entities(payload:ReauthorizedCrossEntityCompletionRequest,request:Request,db:Session=Depends(get_db)): i=_identity(request); return _svc(db,i).entity_completion(payload.model_dump())
@router.post("/regulatory-examination-reauthorized-recovery-outcome-validation/repeated-failure-control-effectiveness")
def controls(payload:RepeatedFailureControlEffectivenessRequest,request:Request,db:Session=Depends(get_db)): i=_identity(request); return _svc(db,i).repeated_failure_effectiveness(payload.model_dump())
@router.post("/regulatory-examination-reauthorized-recovery-outcome-validation/independent-outcome-validation")
def independent(payload:IndependentRecoveryOutcomeAssuranceRequest,request:Request,db:Session=Depends(get_db)): i=_identity(request); return _call(lambda:_svc(db,i).independent_validate(i.principal.user_id,payload.model_dump()))
@router.post("/regulatory-examination-reauthorized-recovery-outcome-validation/regulatory-commitments")
def commitments(payload:ReauthorizedRegulatoryCommitmentCompletionRequest,request:Request,db:Session=Depends(get_db)): i=_identity(request); return _svc(db,i).commitment_completion(payload.model_dump())
@router.post("/regulatory-examination-reauthorized-recovery-outcome-validation/sustainability")
def sustainability(payload:ReauthorizedSustainabilityWindowRequest,request:Request,db:Session=Depends(get_db)): i=_identity(request); return _svc(db,i).sustainability(payload.model_dump())
@router.post("/regulatory-examination-reauthorized-recovery-outcome-validation/reclosure-readiness")
def readiness(payload:ReauthorizedReclosureReadinessRequest,request:Request,db:Session=Depends(get_db)): i=_identity(request); return _svc(db,i).readiness(payload.model_dump())
@router.post("/regulatory-examination-reauthorized-recovery-outcome-validation/residual-risk-reassessment")
def residual(payload:ReauthorizedResidualRiskReassessmentRequest,request:Request,db:Session=Depends(get_db)): i=_identity(request); return _call(lambda:_svc(db,i).residual_risk_reassessment(i.principal.user_id,payload.model_dump()))
@router.post("/regulatory-examination-reauthorized-recovery-outcome-validation/recovery-recertification")
def recertify(payload:ReauthorizedRecoveryRecertificationRequest,request:Request,db:Session=Depends(get_db)): i=_identity(request); return _call(lambda:_svc(db,i).recertify_recovery(i.principal.user_id,payload.model_dump()))
@router.post("/regulatory-examination-reauthorized-recovery-outcome-validation/sustainability-reclosure")
def reclose(payload:ReauthorizedSustainabilityReclosureRequest,request:Request,db:Session=Depends(get_db)): i=_identity(request); return _call(lambda:_svc(db,i).reclose_program(i.principal.user_id,payload.model_dump()))
