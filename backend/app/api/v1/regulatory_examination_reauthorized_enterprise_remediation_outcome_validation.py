from __future__ import annotations
from fastapi import APIRouter, Depends, Header
from app.domain.regulatory_examination_reauthorized_enterprise_remediation_outcome_validation import reauthorized_enterprise_remediation_outcome_contract
from app.schemas.regulatory_examination_reauthorized_enterprise_remediation_outcome_validation import *
from app.services.regulatory_examination_reauthorized_enterprise_remediation_outcome_validation import RegulatoryExaminationReauthorizedEnterpriseRemediationOutcomeValidationService

router = APIRouter(prefix="/regulatory-examination-reauthorized-enterprise-remediation-outcome-validation", tags=["regulatory-examination-reauthorized-enterprise-remediation-outcome-validation"])

def svc(x_tenant_id: str = Header(default="default")):
    return RegulatoryExaminationReauthorizedEnterpriseRemediationOutcomeValidationService(None, x_tenant_id)

@router.get("/model")
def model(): return reauthorized_enterprise_remediation_outcome_contract()

@router.post("/outcomes")
def outcomes(req: EnterpriseRecoveryOutcomeRequest, s=Depends(svc)): return s.outcomes(req.model_dump())

@router.post("/root-cause-treatment-effectiveness")
def root_cause_treatments(req: RootCauseTreatmentEffectivenessRequest, s=Depends(svc)): return s.root_cause_treatments(req.model_dump())

@router.post("/systemic-risk-reduction")
def risk(req: EnterpriseSystemicRiskReductionRequest, s=Depends(svc)): return s.risk_reduction(req.model_dump())

@router.post("/enterprise-control-completion")
def controls(req: EnterpriseControlCompletionRequest, s=Depends(svc)): return s.control_completion(req.model_dump())

@router.post("/repeated-failure-control-effectiveness")
def repeated(req: EnterpriseRepeatedFailureControlEffectivenessRequest, s=Depends(svc)): return s.repeated_failure_effectiveness(req.model_dump())

@router.post("/independent-outcome-assurance")
def independent(req: EnterpriseIndependentOutcomeAssuranceRequest, s=Depends(svc), x_actor_id: str = Header(default="human-user")):
    return s.independent_validate(x_actor_id, req.model_dump())

@router.post("/regulatory-commitment-completion")
def commitments(req: EnterpriseRegulatoryCommitmentCompletionRequest, s=Depends(svc)): return s.commitments(req.model_dump())

@router.post("/blocker-governance")
def blockers(req: EnterpriseBlockerGovernanceRequest, s=Depends(svc)): return s.blockers(req.model_dump())

@router.post("/cross-entity-control-health")
def health(req: EnterpriseControlHealthRequest, s=Depends(svc)): return s.control_health(req.model_dump())

@router.post("/sustainability")
def sustainability(req: EnterpriseSustainabilityWindowRequest, s=Depends(svc)): return s.sustainability(req.model_dump())

@router.post("/reclosure-readiness")
def readiness(req: EnterpriseReclosureReadinessRequest, s=Depends(svc)): return s.readiness(req.model_dump())

@router.post("/residual-risk-reassessment")
def residual(req: EnterpriseResidualRiskReassessmentRequest, s=Depends(svc), x_actor_id: str = Header(default="human-user")):
    return s.residual_risk_reassessment(x_actor_id, req.model_dump())

@router.post("/recovery-recertification")
def recertify(req: EnterpriseRecoveryRecertificationRequest, s=Depends(svc), x_actor_id: str = Header(default="human-user")):
    return s.recertify_recovery(x_actor_id, req.model_dump())

@router.post("/sustainability-reclosure")
def reclose(req: EnterpriseSustainabilityReclosureRequest, s=Depends(svc), x_actor_id: str = Header(default="human-user")):
    return s.reclose_program(x_actor_id, req.model_dump())

@router.post("/dashboard-summary")
def dashboard(req: EnterpriseOutcomeAnalysisRequest, s=Depends(svc)):
    p = {"recovery_program_id": req.recovery_program_id, "evidence_refs": req.evidence_refs, **req.payload}; return s.dashboard(p)

@router.post("/audit-export")
def audit_export(req: EnterpriseOutcomeAnalysisRequest, s=Depends(svc)):
    p = {"recovery_program_id": req.recovery_program_id, "evidence_refs": req.evidence_refs, **req.payload}; return s.audit_export(p)
