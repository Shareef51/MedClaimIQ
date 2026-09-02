from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.regulatory_examination_supervisory_reauthorized_recovery_outcome_validation import supervisory_reauthorized_recovery_outcome_contract
from app.schemas.regulatory_examination_supervisory_reauthorized_recovery_outcome_validation import *
from app.services.regulatory_examination_supervisory_reauthorized_recovery_outcome_validation import RegulatoryExaminationSupervisoryReauthorizedRecoveryOutcomeValidationService

router = APIRouter(tags=["regulatory-examination-supervisory-reauthorized-recovery-outcome-validation"])

def _identity(r: Request):
    i = getattr(r.state, "identity", None)
    if i is None: raise HTTPException(401, "authenticated identity unavailable")
    return i

def _svc(db, i): return RegulatoryExaminationSupervisoryReauthorizedRecoveryOutcomeValidationService(db, i.principal.tenant_id)

def _call(fn):
    try: return fn()
    except PermissionError as e: raise HTTPException(403, str(e)) from e
    except ValueError as e: raise HTTPException(422, str(e)) from e

BASE = "/regulatory-examination-supervisory-reauthorized-recovery-outcome-validation"

@router.get(BASE + "/model")
def model(): return supervisory_reauthorized_recovery_outcome_contract()

@router.post(BASE + "/outcomes")
def outcomes(payload: SupervisoryRecoveryOutcomeRequest, request: Request, db: Session = Depends(get_db)):
    i = _identity(request); return _call(lambda: _svc(db, i).outcomes(payload.model_dump()))

@router.post(BASE + "/systemic-risk-reduction")
def risk(payload: SupervisorySystemicRiskReductionRequest, request: Request, db: Session = Depends(get_db)):
    i = _identity(request); return _svc(db, i).risk_reduction(payload.model_dump())

@router.post(BASE + "/cross-entity-retransformation-completion")
def entities(payload: SupervisoryCrossEntityCompletionRequest, request: Request, db: Session = Depends(get_db)):
    i = _identity(request); return _svc(db, i).entity_completion(payload.model_dump())

@router.post(BASE + "/repeated-failure-control-effectiveness")
def controls(payload: SupervisoryRepeatedFailureControlEffectivenessRequest, request: Request, db: Session = Depends(get_db)):
    i = _identity(request); return _svc(db, i).repeated_failure_effectiveness(payload.model_dump())

@router.post(BASE + "/independent-outcome-validation")
def independent(payload: SupervisoryIndependentOutcomeAssuranceRequest, request: Request, db: Session = Depends(get_db)):
    i = _identity(request); return _call(lambda: _svc(db, i).independent_validate(i.principal.user_id, payload.model_dump()))

@router.post(BASE + "/regulatory-commitments")
def commitments(payload: SupervisoryRegulatoryCommitmentCompletionRequest, request: Request, db: Session = Depends(get_db)):
    i = _identity(request); return _svc(db, i).commitments(payload.model_dump())

@router.post(BASE + "/blockers")
def blockers(payload: SupervisoryBlockerGovernanceRequest, request: Request, db: Session = Depends(get_db)):
    i = _identity(request); return _svc(db, i).blockers(payload.model_dump())

@router.post(BASE + "/sustainability")
def sustainability(payload: SupervisorySustainabilityWindowRequest, request: Request, db: Session = Depends(get_db)):
    i = _identity(request); return _svc(db, i).sustainability(payload.model_dump())

@router.post(BASE + "/reclosure-readiness")
def readiness(payload: SupervisoryReclosureReadinessRequest, request: Request, db: Session = Depends(get_db)):
    i = _identity(request); return _svc(db, i).readiness(payload.model_dump())

@router.post(BASE + "/residual-risk-reassessment")
def residual(payload: SupervisoryResidualRiskReassessmentRequest, request: Request, db: Session = Depends(get_db)):
    i = _identity(request); return _call(lambda: _svc(db, i).residual_risk_reassessment(i.principal.user_id, payload.model_dump()))

@router.post(BASE + "/recovery-recertification")
def recertify(payload: SupervisoryRecoveryRecertificationRequest, request: Request, db: Session = Depends(get_db)):
    i = _identity(request); return _call(lambda: _svc(db, i).recertify_recovery(i.principal.user_id, payload.model_dump()))

@router.post(BASE + "/sustainability-reclosure")
def reclose(payload: SupervisorySustainabilityReclosureRequest, request: Request, db: Session = Depends(get_db)):
    i = _identity(request); return _call(lambda: _svc(db, i).reclose_program(i.principal.user_id, payload.model_dump()))
