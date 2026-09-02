from app.domain.regulatory_examination_renewed_enterprise_remediation_execution import renewed_enterprise_remediation_execution_contract
from app.evaluation.regulatory_examination_renewed_enterprise_remediation_execution import critical_path_status, implementation_drift, recovery_assurance_readiness, residual_systemic_risk
from app.services.regulatory_examination_renewed_enterprise_remediation_execution import RegulatoryExaminationRenewedEnterpriseRemediationExecutionService
import pytest

def test_authority_boundary():
    a=renewed_enterprise_remediation_execution_contract()["authority"]
    assert a["ai_can_approve_control_transformation"] is False
    assert a["ai_can_accept_residual_systemic_risk"] is False
    assert a["ai_can_certify_effectiveness"] is False

def test_critical_path_and_drift_detection():
    cp=critical_path_status({"milestones":[{"status":"blocked","overdue":True}],"dependencies":[{"critical":True,"status":"open"}]})
    assert cp["critical_path_at_risk"] is True
    d=implementation_drift({"expected_controls":[{"control_id":"C1","design_version":"v2"}],"implemented_controls":[{"control_id":"C1","design_version":"v1"}]})
    assert d["implementation_drift_detected"] is True

def test_recovery_readiness_blocks_incomplete_program():
    r=recovery_assurance_readiness({"all_required_milestones_complete":True,"implementation_evidence_complete":True,"independent_recovery_testing_passed":False,"cross_entity_validation_complete":True})
    assert r["ready_for_human_residual_risk_reassessment"] is False

def test_human_only_residual_risk_acceptance():
    svc=RegulatoryExaminationRenewedEnterpriseRemediationExecutionService(None,"t1")
    with pytest.raises(PermissionError):
        svc.decide_residual_risk("ai",{"actor_role":"ai_agent","decision":"accept","rationale":"x","readiness":{}})
    rr=residual_systemic_risk({"baseline_risk_score":90,"current_risk_score":30})
    assert rr["risk_reduction_percent"] == pytest.approx(66.67)
