from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.regulatory_reopened_outcome_validation import reopened_outcome_validation_contract
from app.schemas.regulatory_reopened_outcome_validation import *
from app.services.regulatory_reopened_outcome_validation import RegulatoryReopenedOutcomeValidationService
from app.services.review_workbench import ReviewConflictError, ReviewLockError

router = APIRouter(tags=["regulatory-reopened-outcome-validation"])

def _i(r):
    x = getattr(r.state, "identity", None)
    if x is None: raise HTTPException(401, "authenticated identity unavailable")
    return x

def _run(db, fn):
    try:
        r = fn(); db.commit(); return r
    except Exception as e:
        db.rollback()
        if isinstance(e, LookupError): raise HTTPException(404, str(e)) from e
        if isinstance(e, (ReviewConflictError, ReviewLockError)): raise HTTPException(409, str(e)) from e
        if isinstance(e, (ValueError, PermissionError)): raise HTTPException(400, str(e)) from e
        raise

def _svc(db, t): return RegulatoryReopenedOutcomeValidationService(db, t)

@router.get('/regulatory-reopened-outcomes/model')
def model(): return reopened_outcome_validation_contract()

@router.get('/regulatory-reopened-outcomes/dashboard')
def dashboard(request: Request, db: Session = Depends(get_db)):
    i = _i(request); return _run(db, lambda: _svc(db, i.principal.tenant_id).dashboard(i.principal.user_id))

@router.post('/regulatory-reopened-outcomes')
def create_outcome(payload: ReopenedOutcomeRequest, request: Request, db: Session = Depends(get_db)):
    i = _i(request); x = _run(db, lambda: _svc(db, i.principal.tenant_id).register_outcome(i.principal.user_id, **payload.model_dump()))
    return {"outcome_id": x.outcome_id, "status": x.status}

@router.post('/regulatory-reopened-outcomes/revalidations')
def revalidate(payload: IndependentRevalidationRequest, request: Request, db: Session = Depends(get_db)):
    i = _i(request); x = _run(db, lambda: _svc(db, i.principal.tenant_id).record_revalidation(i.principal.user_id, **payload.model_dump()))
    return {"revalidation_id": x.revalidation_id, "independently_validated": x.independently_validated}

@router.post('/regulatory-reopened-outcomes/closure-assurance')
def assurance(payload: ClosureAssuranceRequest, request: Request, db: Session = Depends(get_db)):
    i = _i(request); x = _run(db, lambda: _svc(db, i.principal.tenant_id).create_assurance(i.principal.user_id, **payload.model_dump()))
    return {"assurance_id": x.assurance_id, "version": x.version, "readiness_score": x.readiness_score, "blockers": x.blockers, "status": x.status}

@router.post('/regulatory-reopened-outcomes/closure-assurance/{assurance_id}/recertify')
def recertify(assurance_id: str, payload: HumanRecertificationRequest, request: Request, db: Session = Depends(get_db)):
    i = _i(request); x = _run(db, lambda: _svc(db, i.principal.tenant_id).recertify(i.principal.user_id, assurance_id, **payload.model_dump()))
    return {"recertification_id": x.recertification_id, "decision": x.decision}
