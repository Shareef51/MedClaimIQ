from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.regulatory_examination_reopened_reauthorized_enterprise_remediation_investigation import reopened_reauthorized_enterprise_remediation_investigation_contract
from app.schemas.regulatory_examination_reopened_reauthorized_enterprise_remediation_investigation import *
from app.services.regulatory_examination_reopened_reauthorized_enterprise_remediation_investigation import RegulatoryExaminationReopenedReauthorizedEnterpriseRemediationInvestigationService

router = APIRouter(tags=["regulatory-examination-reopened-reauthorized-enterprise-remediation-investigation"])
BASE = "/regulatory-examination-reopened-reauthorized-enterprise-remediation-investigation"

def _identity(r: Request):
    i = getattr(r.state, "identity", None)
    if i is None: raise HTTPException(401, "authenticated identity unavailable")
    return i

def _svc(db, i): return RegulatoryExaminationReopenedReauthorizedEnterpriseRemediationInvestigationService(db, i.principal.tenant_id)
def _call(fn):
    try: return fn()
    except PermissionError as e: raise HTTPException(403, str(e)) from e
    except ValueError as e: raise HTTPException(422, str(e)) from e

@router.get(BASE + "/model")
def model(): return reopened_reauthorized_enterprise_remediation_investigation_contract()
@router.post(BASE + "/investigations")
def investigation(payload: ReopenedReauthorizedEnterpriseRemediationInvestigationCreate, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _call(lambda:_svc(db,i).create_investigation(i.principal.user_id,payload.model_dump()))
@router.post(BASE + "/multi-cycle-remediation-evidence")
def evidence(payload: MultiCycleRemediationEvidenceRequest, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _svc(db,i).reconstruct_evidence(payload.model_dump())
@router.post(BASE + "/persistent-emergent-treatment-failures")
def treatments(payload: PersistentEmergentTreatmentFailureRequest, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _svc(db,i).analyze_treatment_failures(payload.model_dump())
@router.post(BASE + "/systemic-remediation-root-causes")
def roots(payload: SystemicRemediationFailureRootCauseRequest, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _svc(db,i).reconstruct_root_causes(payload.model_dump())
@router.post(BASE + "/prior-recertification-reclosure-assumptions")
def assumptions(payload: PriorRecertificationReclosureAssumptionRequest, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _svc(db,i).validate_assumptions(payload.model_dump())
@router.post(BASE + "/systemic-control-retransformation-failures")
def controls(payload: RepeatedSystemicControlRetransformationFailureRequest, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _svc(db,i).analyze_control_failures(payload.model_dump())
@router.post(BASE + "/cross-entity-causal-propagation")
def causality(payload: RemediationCrossEntityCausalPropagationRequest, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _svc(db,i).causal_map(payload.model_dump())
@router.post(BASE + "/regulatory-commitment-followup-impact")
def regulatory(payload: RemediationRegulatoryCommitmentFollowupImpactRequest, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _svc(db,i).regulatory_impact(payload.model_dump())
@router.post(BASE + "/systemic-remediation-failure-classification")
def classification(payload: SystemicRemediationFailureClassificationRequest, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _svc(db,i).classify_failure(payload.model_dump())
@router.post(BASE + "/root-cause-confirmations")
def root_confirmation(payload: RemediationRootCauseConfirmationCreate, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _call(lambda:_svc(db,i).confirm_root_causes(i.principal.user_id,payload.model_dump()))
@router.post(BASE + "/classification-confirmations")
def class_confirmation(payload: SystemicRemediationFailureClassificationConfirmationCreate, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _call(lambda:_svc(db,i).confirm_systemic_failure_classification(i.principal.user_id,payload.model_dump()))
@router.post(BASE + "/strategy-candidates")
def strategy(payload: RenewedEnterpriseRemediationStrategyCandidateCreate, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _call(lambda:_svc(db,i).create_strategy_candidate(i.principal.user_id,payload.model_dump()))
@router.post(BASE + "/independent-challenges")
def challenge(payload: EnterpriseRemediationIndependentChallengeCreate, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _call(lambda:_svc(db,i).independent_challenge(i.principal.user_id,payload.model_dump()))
@router.post(BASE + "/investigation-conclusions")
def conclusion(payload: ReopenedRemediationInvestigationConclusionCreate, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _call(lambda:_svc(db,i).conclude_investigation(i.principal.user_id,payload.model_dump()))
@router.post(BASE + "/reauthorization-readiness")
def readiness(payload: EnterpriseRemediationReauthorizationReadinessRequest, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _svc(db,i).readiness(payload.model_dump())
@router.post(BASE + "/reauthorizations")
def authorize(payload: EnterpriseRemediationReauthorizationCreate, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _call(lambda:_svc(db,i).authorize_enterprise_remediation(i.principal.user_id,payload.model_dump()))
@router.post(BASE + "/dashboard")
def dashboard(payload: ReopenedRemediationDashboardRequest, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _svc(db,i).dashboard(payload.model_dump())
@router.post(BASE + "/audit-export")
def audit_export(payload: ReopenedRemediationAuditExportRequest, request: Request, db: Session=Depends(get_db)): i=_identity(request); return _svc(db,i).audit_export(payload.model_dump())
