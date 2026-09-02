from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.regulatory_examination_reopened_enterprise_recovery_investigation import reopened_enterprise_recovery_investigation_contract
from app.schemas.regulatory_examination_reopened_enterprise_recovery_investigation import *
from app.services.regulatory_examination_reopened_enterprise_recovery_investigation import RegulatoryExaminationReopenedEnterpriseRecoveryInvestigationService

router = APIRouter(tags=["regulatory-examination-reopened-enterprise-recovery-investigation"])
BASE = "/regulatory-examination-reopened-enterprise-recovery-investigation"

def _identity(r: Request):
    i = getattr(r.state, "identity", None)
    if i is None: raise HTTPException(401, "authenticated identity unavailable")
    return i

def _svc(db, i): return RegulatoryExaminationReopenedEnterpriseRecoveryInvestigationService(db, i.principal.tenant_id)
def _call(fn):
    try: return fn()
    except PermissionError as e: raise HTTPException(403, str(e)) from e
    except ValueError as e: raise HTTPException(422, str(e)) from e

@router.get(BASE + "/model")
def model(): return reopened_enterprise_recovery_investigation_contract()
@router.post(BASE + "/investigations")
def investigation(payload: ReopenedEnterpriseRecoveryInvestigationCreate, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _call(lambda:_svc(db,i).create_investigation(i.principal.user_id,payload.model_dump()))
@router.post(BASE + "/multi-cycle-evidence")
def evidence(payload: MultiCycleEnterpriseEvidenceRequest, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _svc(db,i).reconstruct_evidence(payload.model_dump())
@router.post(BASE + "/systemic-root-causes")
def roots(payload: SystemicRecoveryFailureRootCauseRequest, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _svc(db,i).reconstruct_root_causes(payload.model_dump())
@router.post(BASE + "/prior-enterprise-recertification-reclosure-assumptions")
def assumptions(payload: PriorEnterpriseRecertificationReclosureAssumptionRequest, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _svc(db,i).validate_assumptions(payload.model_dump())
@router.post(BASE + "/systemic-control-retransformation-failures")
def controls(payload: RepeatedSystemicControlRetransformationFailureRequest, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _svc(db,i).analyze_control_failures(payload.model_dump())
@router.post(BASE + "/cross-entity-causal-propagation")
def causality(payload: EnterpriseCrossEntityCausalPropagationRequest, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _svc(db,i).causal_map(payload.model_dump())
@router.post(BASE + "/regulatory-commitment-followup-impact")
def regulatory(payload: RegulatoryCommitmentFollowupImpactRequest, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _svc(db,i).regulatory_impact(payload.model_dump())
@router.post(BASE + "/enterprise-systemic-failure-classification")
def classification(payload: EnterpriseSystemicRecoveryFailureClassificationRequest, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _svc(db,i).classify_failure(payload.model_dump())
@router.post(BASE + "/root-cause-confirmations")
def confirm_roots(payload: EnterpriseRootCauseConfirmationCreate, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _call(lambda:_svc(db,i).confirm_root_causes(i.principal.user_id,payload.model_dump()))
@router.post(BASE + "/systemic-failure-classification-confirmations")
def confirm_classification(payload: EnterpriseSystemicFailureClassificationConfirmationCreate, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _call(lambda:_svc(db,i).confirm_systemic_failure_classification(i.principal.user_id,payload.model_dump()))
@router.post(BASE + "/renewed-remediation-strategy-candidates")
def strategy(payload: RenewedEnterpriseRemediationStrategyCandidateCreate, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _call(lambda:_svc(db,i).create_strategy_candidate(i.principal.user_id,payload.model_dump()))
@router.post(BASE + "/independent-challenges")
def challenge(payload: EnterpriseRecoveryIndependentChallengeCreate, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _call(lambda:_svc(db,i).independent_challenge(i.principal.user_id,payload.model_dump()))
@router.post(BASE + "/investigation-conclusions")
def conclusion(payload: ReopenedEnterpriseRecoveryInvestigationConclusionCreate, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _call(lambda:_svc(db,i).conclude_investigation(i.principal.user_id,payload.model_dump()))
@router.post(BASE + "/reauthorization-readiness")
def readiness(payload: EnterpriseRemediationReauthorizationReadinessRequest, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _svc(db,i).readiness(payload.model_dump())
@router.post(BASE + "/remediation-reauthorizations")
def reauthorize(payload: EnterpriseRemediationReauthorizationCreate, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _call(lambda:_svc(db,i).authorize_enterprise_remediation(i.principal.user_id,payload.model_dump()))
@router.post(BASE + "/dashboard")
def dashboard(payload: ReopenedEnterpriseRecoveryDashboardRequest, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _svc(db,i).dashboard(payload.model_dump())
@router.post(BASE + "/audit-export")
def audit_export(payload: ReopenedEnterpriseRecoveryAuditExportRequest, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _svc(db,i).audit_export(payload.model_dump())
