from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.regulatory_examination_reclosed_enterprise_recovery_surveillance import reclosed_enterprise_recovery_surveillance_contract
from app.schemas.regulatory_examination_reclosed_enterprise_recovery_surveillance import *
from app.services.regulatory_examination_reclosed_enterprise_recovery_surveillance import RegulatoryExaminationReclosedEnterpriseRecoverySurveillanceService

router = APIRouter(tags=["regulatory-examination-reclosed-enterprise-recovery-surveillance"])
BASE = "/regulatory-examination-reclosed-enterprise-recovery-surveillance"

def _identity(request: Request):
    identity = getattr(request.state, "identity", None)
    if identity is None:
        raise HTTPException(401, "authenticated identity unavailable")
    return identity

def _svc(db, identity):
    return RegulatoryExaminationReclosedEnterpriseRecoverySurveillanceService(db, identity.principal.tenant_id)

def _call(fn):
    try:
        return fn()
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

@router.get(BASE + "/model")
def model():
    return reclosed_enterprise_recovery_surveillance_contract()

@router.post(BASE + "/multi-cycle-decay")
def decay(payload: EnterpriseRecoveryDecayRequest, request: Request, db: Session = Depends(get_db)):
    identity = _identity(request)
    return _call(lambda: _svc(db, identity).decay(payload.model_dump()))

@router.post(BASE + "/systemic-control-retransformation-regression")
def regression(payload: SystemicControlRetransformationRegressionRequest, request: Request, db: Session = Depends(get_db)):
    identity = _identity(request)
    return _svc(db, identity).control_regression(payload.model_dump())

@router.post(BASE + "/systemic-risk-rebound")
def rebound(payload: EnterpriseRiskReboundRequest, request: Request, db: Session = Depends(get_db)):
    identity = _identity(request)
    return _svc(db, identity).rebound(payload.model_dump())

@router.post(BASE + "/cross-entity-recurrence")
def recurrence(payload: EnterpriseCrossEntityRecurrenceRequest, request: Request, db: Session = Depends(get_db)):
    identity = _identity(request)
    return _svc(db, identity).recurrence(payload.model_dump())

@router.post(BASE + "/prior-reclosure-comparison")
def compare(payload: PriorEnterpriseReclosureComparisonRequest, request: Request, db: Session = Depends(get_db)):
    identity = _identity(request)
    return _svc(db, identity).compare(payload.model_dump())

@router.post(BASE + "/examination-finding-correlation")
def findings(payload: EnterpriseExaminationFindingCorrelationRequest, request: Request, db: Session = Depends(get_db)):
    identity = _identity(request)
    return _svc(db, identity).correlate_findings(payload.model_dump())

@router.post(BASE + "/regulator-followups")
def followups(payload: EnterpriseRegulatorFollowupLinkageRequest, request: Request, db: Session = Depends(get_db)):
    identity = _identity(request)
    return _svc(db, identity).regulator_followups(payload.model_dump())

@router.post(BASE + "/enterprise-materiality")
def materiality(payload: EnterpriseMaterialityRequest, request: Request, db: Session = Depends(get_db)):
    identity = _identity(request)
    return _svc(db, identity).materiality(payload.model_dump())

@router.post(BASE + "/investigations")
def investigation(payload: EnterpriseRecoveryDecayInvestigationCreate, request: Request, db: Session = Depends(get_db)):
    identity = _identity(request)
    return _call(lambda: _svc(db, identity).create_investigation(identity.principal.user_id, payload.model_dump()))

@router.post(BASE + "/independent-reassessments")
def reassessment(payload: EnterpriseIndependentReassessmentCreate, request: Request, db: Session = Depends(get_db)):
    identity = _identity(request)
    return _call(lambda: _svc(db, identity).independent_reassess(identity.principal.user_id, payload.model_dump()))

@router.post(BASE + "/enterprise-challenges")
def challenge(payload: EnterpriseExecutiveInternalAuditChallengeCreate, request: Request, db: Session = Depends(get_db)):
    identity = _identity(request)
    return _call(lambda: _svc(db, identity).enterprise_challenge(identity.principal.user_id, payload.model_dump()))

@router.post(BASE + "/reopening-readiness")
def readiness(payload: EnterpriseReopeningReadinessRequest, request: Request, db: Session = Depends(get_db)):
    identity = _identity(request)
    return _svc(db, identity).readiness(payload.model_dump())

@router.post(BASE + "/reopening-decisions")
def reopening(payload: EnterpriseReopeningDecisionCreate, request: Request, db: Session = Depends(get_db)):
    identity = _identity(request)
    return _call(lambda: _svc(db, identity).decide_reopening(identity.principal.user_id, payload.model_dump()))

@router.post(BASE + "/dashboard")
def dashboard(payload: EnterpriseSurveillanceDashboardRequest, request: Request, db: Session = Depends(get_db)):
    identity = _identity(request)
    return _call(lambda: _svc(db, identity).dashboard(payload.model_dump()))

@router.post(BASE + "/audit-export")
def audit_export(payload: EnterpriseAuditExportRequest, request: Request, db: Session = Depends(get_db)):
    identity = _identity(request)
    return _call(lambda: _svc(db, identity).audit_export(payload.model_dump()))
