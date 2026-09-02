from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.regulatory_examination_reclosed_supervisory_recovery_surveillance import reclosed_supervisory_recovery_surveillance_contract
from app.schemas.regulatory_examination_reclosed_supervisory_recovery_surveillance import *
from app.services.regulatory_examination_reclosed_supervisory_recovery_surveillance import RegulatoryExaminationReclosedSupervisoryRecoverySurveillanceService

router = APIRouter(tags=["regulatory-examination-reclosed-supervisory-recovery-surveillance"])
BASE = "/regulatory-examination-reclosed-supervisory-recovery-surveillance"

def _identity(r: Request):
    i=getattr(r.state, "identity", None)
    if i is None: raise HTTPException(401, "authenticated identity unavailable")
    return i

def _svc(db, i): return RegulatoryExaminationReclosedSupervisoryRecoverySurveillanceService(db, i.principal.tenant_id)
def _call(fn):
    try: return fn()
    except PermissionError as e: raise HTTPException(403, str(e)) from e
    except ValueError as e: raise HTTPException(422, str(e)) from e

@router.get(BASE + "/model")
def model(): return reclosed_supervisory_recovery_surveillance_contract()
@router.post(BASE + "/multi-cycle-decay")
def decay(payload: SupervisoryRecoveryDecayRequest, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _call(lambda:_svc(db,i).decay(payload.model_dump()))
@router.post(BASE + "/control-retransformation-regression")
def regression(payload: SupervisoryControlRetransformationRegressionRequest, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _svc(db,i).control_regression(payload.model_dump())
@router.post(BASE + "/systemic-risk-rebound")
def rebound(payload: SupervisoryRiskReboundRequest, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _svc(db,i).rebound(payload.model_dump())
@router.post(BASE + "/cross-entity-recurrence")
def recurrence(payload: SupervisoryCrossEntityRecurrenceRequest, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _svc(db,i).recurrence(payload.model_dump())
@router.post(BASE + "/prior-reclosure-comparison")
def compare(payload: PriorSupervisoryReclosureComparisonRequest, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _svc(db,i).compare(payload.model_dump())
@router.post(BASE + "/examination-finding-correlation")
def findings(payload: SupervisoryExaminationFindingCorrelationRequest, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _svc(db,i).correlate_findings(payload.model_dump())
@router.post(BASE + "/regulator-followups")
def followups(payload: SupervisoryRegulatorFollowupLinkageRequest, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _svc(db,i).regulator_followups(payload.model_dump())
@router.post(BASE + "/enterprise-materiality")
def materiality(payload: EnterpriseSupervisoryMaterialityRequest, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _svc(db,i).materiality(payload.model_dump())
@router.post(BASE + "/investigations")
def investigation(payload: SupervisoryRecoveryDecayInvestigationCreate, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _call(lambda:_svc(db,i).create_investigation(i.principal.user_id, payload.model_dump()))
@router.post(BASE + "/independent-reassessments")
def reassessment(payload: SupervisoryIndependentReassessmentCreate, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _call(lambda:_svc(db,i).independent_reassess(i.principal.user_id, payload.model_dump()))
@router.post(BASE + "/supervisory-challenges")
def challenge(payload: SupervisoryExecutiveInternalAuditChallengeCreate, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _call(lambda:_svc(db,i).supervisory_challenge(i.principal.user_id, payload.model_dump()))
@router.post(BASE + "/reopening-readiness")
def readiness(payload: SupervisoryEnterpriseReopeningReadinessRequest, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _svc(db,i).readiness(payload.model_dump())
@router.post(BASE + "/reopening-decisions")
def reopening(payload: SupervisoryEnterpriseReopeningDecisionCreate, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _call(lambda:_svc(db,i).decide_reopening(i.principal.user_id, payload.model_dump()))
