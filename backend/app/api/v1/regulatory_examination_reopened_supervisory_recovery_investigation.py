from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.regulatory_examination_reopened_supervisory_recovery_investigation import reopened_supervisory_recovery_investigation_contract
from app.schemas.regulatory_examination_reopened_supervisory_recovery_investigation import *
from app.services.regulatory_examination_reopened_supervisory_recovery_investigation import RegulatoryExaminationReopenedSupervisoryRecoveryInvestigationService

router = APIRouter(tags=["regulatory-examination-reopened-supervisory-recovery-investigation"])
BASE = "/regulatory-examination-reopened-supervisory-recovery-investigation"

def _identity(r: Request):
    i = getattr(r.state, "identity", None)
    if i is None: raise HTTPException(401, "authenticated identity unavailable")
    return i

def _svc(db, i): return RegulatoryExaminationReopenedSupervisoryRecoveryInvestigationService(db, i.principal.tenant_id)
def _call(fn):
    try: return fn()
    except PermissionError as e: raise HTTPException(403, str(e)) from e
    except ValueError as e: raise HTTPException(422, str(e)) from e

@router.get(BASE + "/model")
def model(): return reopened_supervisory_recovery_investigation_contract()
@router.post(BASE + "/investigations")
def investigation(payload: ReopenedSupervisoryRecoveryInvestigationCreate, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _call(lambda:_svc(db,i).create_investigation(i.principal.user_id,payload.model_dump()))
@router.post(BASE + "/multi-cycle-evidence")
def evidence(payload: MultiCycleSupervisoryEvidenceRequest, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _svc(db,i).reconstruct_evidence(payload.model_dump())
@router.post(BASE + "/root-causes")
def roots(payload: PersistentEmergentRootCauseRequest, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _svc(db,i).reconstruct_root_causes(payload.model_dump())
@router.post(BASE + "/recertification-reclosure-assumptions")
def assumptions(payload: PriorRecertificationReclosureAssumptionValidationRequest, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _svc(db,i).validate_assumptions(payload.model_dump())
@router.post(BASE + "/control-retransformation-failures")
def controls(payload: RepeatedControlRetransformationFailureRequest, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _svc(db,i).analyze_retransformation(payload.model_dump())
@router.post(BASE + "/cross-entity-causal-propagation")
def causality(payload: CrossEntityCausalPropagationRequest, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _svc(db,i).causal_map(payload.model_dump())
@router.post(BASE + "/regulator-followup-impact")
def regulator(payload: ReopenedSupervisoryRegulatorFollowupImpactRequest, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _svc(db,i).regulator_impact(payload.model_dump())
@router.post(BASE + "/enterprise-systemic-failure-classification")
def classification(payload: EnterpriseSystemicFailureClassificationRequest, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _svc(db,i).classify_failure(payload.model_dump())
@router.post(BASE + "/root-cause-confirmations")
def confirm_roots(payload: HumanRootCauseConfirmationCreate, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _call(lambda:_svc(db,i).confirm_root_causes(i.principal.user_id,payload.model_dump()))
@router.post(BASE + "/systemic-failure-classification-confirmations")
def confirm_classification(payload: HumanSystemicFailureClassificationCreate, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _call(lambda:_svc(db,i).confirm_systemic_failure_classification(i.principal.user_id,payload.model_dump()))
@router.post(BASE + "/strategy-candidates")
def strategy(payload: RenewedEnterpriseRecoveryStrategyCandidateCreate, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _call(lambda:_svc(db,i).create_strategy_candidate(i.principal.user_id,payload.model_dump()))
@router.post(BASE + "/independent-challenges")
def challenge(payload: ReopenedSupervisoryRecoveryIndependentChallengeCreate, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _call(lambda:_svc(db,i).independent_challenge(i.principal.user_id,payload.model_dump()))
@router.post(BASE + "/conclusions")
def conclusion(payload: ReopenedSupervisoryRecoveryInvestigationConclusionCreate, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _call(lambda:_svc(db,i).conclude_investigation(i.principal.user_id,payload.model_dump()))
@router.post(BASE + "/reauthorization-readiness")
def readiness(payload: EnterpriseRecoveryReauthorizationReadinessRequest, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _svc(db,i).readiness(payload.model_dump())
@router.post(BASE + "/reauthorizations")
def reauthorize(payload: EnterpriseRecoveryReauthorizationCreate, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _call(lambda:_svc(db,i).authorize_recovery(i.principal.user_id,payload.model_dump()))
@router.post(BASE + "/supervisory-dashboard")
def dashboard(payload: ReopenedSupervisoryRecoveryDashboardRequest, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _svc(db,i).dashboard(payload.model_dump())
@router.post(BASE + "/audit-export")
def audit_export(payload: ReopenedSupervisoryRecoveryAuditExportRequest, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _svc(db,i).audit_export(payload.model_dump())
