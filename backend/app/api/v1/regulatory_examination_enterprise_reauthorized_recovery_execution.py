from __future__ import annotations
from fastapi import APIRouter, Depends, Header
from app.domain.regulatory_examination_enterprise_reauthorized_recovery_execution import enterprise_reauthorized_recovery_execution_contract
from app.schemas.regulatory_examination_enterprise_reauthorized_recovery_execution import *
from app.services.regulatory_examination_enterprise_reauthorized_recovery_execution import RegulatoryExaminationEnterpriseReauthorizedRecoveryExecutionService

router = APIRouter(prefix="/regulatory-examination-enterprise-reauthorized-recovery-execution", tags=["regulatory-examination-enterprise-reauthorized-recovery-execution"])

def svc(x_tenant_id: str = Header(default="default")):
    return RegulatoryExaminationEnterpriseReauthorizedRecoveryExecutionService(None, x_tenant_id)

@router.get("/model")
def model(): return enterprise_reauthorized_recovery_execution_contract()

@router.post("/programs")
def create_program(req: EnterpriseRecoveryProgramCreate, s=Depends(svc), x_actor_id: str = Header(default="human-user")):
    return s.create_program(x_actor_id, req.model_dump())

@router.post("/progress")
def progress(req: EnterpriseRecoveryAnalysisRequest, s=Depends(svc)): return s.progress(req.model_dump())

@router.post("/control-retransformation")
def control_retransformation(req: EnterpriseRecoveryAnalysisRequest, s=Depends(svc)): return s.control_retransformation(req.model_dump())

@router.post("/deployment-sequence")
def deployment_sequence(req: EnterpriseRecoveryAnalysisRequest, s=Depends(svc)): return s.deployment_sequence(req.model_dump())

@router.post("/commitment-alignment")
def commitment_alignment(req: EnterpriseRecoveryAnalysisRequest, s=Depends(svc)): return s.commitment_alignment(req.model_dump())

@router.post("/critical-path")
def critical_path(req: EnterpriseRecoveryAnalysisRequest, s=Depends(svc)): return s.critical_path(req.model_dump())

@router.post("/implementation-drift")
def drift(req: EnterpriseRecoveryAnalysisRequest, s=Depends(svc)): return s.detect_drift(req.model_dump())

@router.post("/systemic-recovery-kpis")
def kpis(req: EnterpriseRecoveryAnalysisRequest, s=Depends(svc)): return s.kpis(req.model_dump())

@router.post("/enterprise-control-validation")
def enterprise_validation(req: EnterpriseRecoveryAnalysisRequest, s=Depends(svc)): return s.enterprise_validation(req.model_dump())

@router.post("/blocker-escalation")
def blocker_escalation(req: EnterpriseRecoveryAnalysisRequest, s=Depends(svc)): return s.blocker_escalation(req.model_dump())

@router.post("/control-retransformation-approvals")
def approve_control(req: ControlRetransformationApprovalCreate, s=Depends(svc), x_actor_id: str = Header(default="human-user")):
    return s.approve_control_retransformation(x_actor_id, req.model_dump())

@router.post("/implementation-checkpoints")
def checkpoint(req: ImplementationCheckpointCreate, s=Depends(svc), x_actor_id: str = Header(default="human-user")):
    return s.create_checkpoint(x_actor_id, req.model_dump())

@router.post("/independent-effectiveness-assurance")
def assurance(req: IndependentEffectivenessAssuranceCreate, s=Depends(svc), x_actor_id: str = Header(default="human-user")):
    return s.independent_assurance(x_actor_id, req.model_dump())

@router.post("/execution-readiness")
def readiness(req: ExecutionReadinessRequest, s=Depends(svc)): return s.readiness(req.model_dump())

@router.post("/executive-supervisory-reviews")
def executive_review(req: ExecutiveSupervisoryReviewCreate, s=Depends(svc), x_actor_id: str = Header(default="human-user")):
    return s.executive_review(x_actor_id, req.model_dump())

@router.post("/dashboard-summary")
def dashboard(req: EnterpriseRecoveryAnalysisRequest, s=Depends(svc)): return s.dashboard(req.model_dump())

@router.post("/audit-export")
def audit_export(req: AuditExportRequest, s=Depends(svc)): return s.audit_export(req.model_dump())
