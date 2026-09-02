from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.regulatory_examination_renewed_recovery_outcome_validation import renewed_recovery_outcome_contract
from app.schemas.regulatory_examination_renewed_recovery_outcome_validation import (
    CrossEntityCompletionRequest,
    IndependentRecoveryEffectivenessRequest,
    RecoveryRecertificationRequest,
    RegulatoryCommitmentCompletionRequest,
    RenewedRecoveryOutcomeRequest,
    ReclosureReadinessRequest,
    ResidualRiskReassessmentRequest,
    SustainabilityReclosureRequest,
    SustainabilityWindowRequest,
    SystemicRiskReductionRequest,
)
from app.services.regulatory_examination_renewed_recovery_outcome_validation import RegulatoryExaminationRenewedRecoveryOutcomeValidationService

router = APIRouter(tags=["regulatory-examination-renewed-recovery-outcome-validation"])


def _identity(request: Request):
    identity = getattr(request.state, "identity", None)
    if identity is None:
        raise HTTPException(401, "authenticated identity unavailable")
    return identity


def _svc(db, identity):
    return RegulatoryExaminationRenewedRecoveryOutcomeValidationService(db, identity.principal.tenant_id)


def _call(fn):
    try:
        return fn()
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/regulatory-examination-renewed-recovery-outcome-validation/model")
def model():
    return renewed_recovery_outcome_contract()


@router.post("/regulatory-examination-renewed-recovery-outcome-validation/outcomes")
def outcomes(payload: RenewedRecoveryOutcomeRequest, request: Request, db: Session = Depends(get_db)):
    identity = _identity(request)
    return _svc(db, identity).outcomes(payload.model_dump())


@router.post("/regulatory-examination-renewed-recovery-outcome-validation/systemic-risk-reduction")
def risk(payload: SystemicRiskReductionRequest, request: Request, db: Session = Depends(get_db)):
    identity = _identity(request)
    return _svc(db, identity).risk_reduction(payload.model_dump())


@router.post("/regulatory-examination-renewed-recovery-outcome-validation/cross-entity-completion")
def entities(payload: CrossEntityCompletionRequest, request: Request, db: Session = Depends(get_db)):
    identity = _identity(request)
    return _svc(db, identity).entity_completion(payload.model_dump())


@router.post("/regulatory-examination-renewed-recovery-outcome-validation/independent-recovery-validation")
def independent(payload: IndependentRecoveryEffectivenessRequest, request: Request, db: Session = Depends(get_db)):
    identity = _identity(request)
    return _call(lambda: _svc(db, identity).independent_validate(identity.principal.user_id, payload.model_dump()))


@router.post("/regulatory-examination-renewed-recovery-outcome-validation/regulatory-commitments")
def commitments(payload: RegulatoryCommitmentCompletionRequest, request: Request, db: Session = Depends(get_db)):
    identity = _identity(request)
    return _svc(db, identity).commitment_completion(payload.model_dump())


@router.post("/regulatory-examination-renewed-recovery-outcome-validation/sustainability")
def sustainability(payload: SustainabilityWindowRequest, request: Request, db: Session = Depends(get_db)):
    identity = _identity(request)
    return _svc(db, identity).sustainability(payload.model_dump())


@router.post("/regulatory-examination-renewed-recovery-outcome-validation/reclosure-readiness")
def readiness(payload: ReclosureReadinessRequest, request: Request, db: Session = Depends(get_db)):
    identity = _identity(request)
    return _svc(db, identity).readiness(payload.model_dump())


@router.post("/regulatory-examination-renewed-recovery-outcome-validation/residual-risk-reassessment")
def residual_risk(payload: ResidualRiskReassessmentRequest, request: Request, db: Session = Depends(get_db)):
    identity = _identity(request)
    return _call(lambda: _svc(db, identity).residual_risk_reassessment(identity.principal.user_id, payload.model_dump()))


@router.post("/regulatory-examination-renewed-recovery-outcome-validation/recovery-recertification")
def recertify(payload: RecoveryRecertificationRequest, request: Request, db: Session = Depends(get_db)):
    identity = _identity(request)
    return _call(lambda: _svc(db, identity).recertify_recovery(identity.principal.user_id, payload.model_dump()))


@router.post("/regulatory-examination-renewed-recovery-outcome-validation/sustainability-reclosure")
def reclose(payload: SustainabilityReclosureRequest, request: Request, db: Session = Depends(get_db)):
    identity = _identity(request)
    return _call(lambda: _svc(db, identity).reclose_program(identity.principal.user_id, payload.model_dump()))
