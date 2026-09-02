import pytest
from app.domain.regulatory_examination_renewed_remediation_outcome_validation import renewed_remediation_outcome_validation_contract
from app.evaluation.regulatory_examination_renewed_remediation_outcome_validation import outcome_measurement, reclosure_readiness, sustainability_status
from app.services.regulatory_examination_renewed_remediation_outcome_validation import RegulatoryExaminationRenewedRemediationOutcomeValidationService

def test_authority_boundary():
    a=renewed_remediation_outcome_validation_contract()["authority"]
    assert a["ai_can_accept_residual_systemic_risk"] is False
    assert a["ai_can_certify_recovery_effectiveness"] is False
    assert a["ai_can_reclose_intervention_program"] is False

def test_outcome_measurement_requires_complete_recovery():
    o=outcome_measurement({"baseline_risk_score":90,"current_risk_score":30,"independent_tests":[{"result":"pass"}],"expected_entity_ids":["US","EU"],"completed_entity_ids":["US"]})
    assert o["risk_reduction_percent"] == pytest.approx(66.67)
    assert o["cross_entity_completion_percent"] == 50.0
    assert o["recovery_effective_candidate"] is False

def test_reclosure_readiness_blocks_missing_gates():
    r=reclosure_readiness({"all_workstreams_complete":True,"implementation_evidence_complete":True,"independent_recovery_validation_passed":True,"cross_entity_reconciliation_complete":True,"regulatory_commitments_reconciled":True,"unresolved_blockers":0,"sustainability_window_complete":False,"residual_risk_human_accepted":True})
    assert r["ready_for_human_executive_reclosure"] is False
    assert "sustainability_window_incomplete" in r["blockers"]

def test_human_only_reclosure_and_reopen_signal():
    svc=RegulatoryExaminationRenewedRemediationOutcomeValidationService(None,"t1")
    with pytest.raises(PermissionError):
        svc.reclose("ai",{"actor_role":"ai_agent","decision":"reclose","rationale":"x","readiness":{}})
    s=sustainability_status({"observations":[{"control_health":"degraded","recurrence_detected":True}]})
    assert s["reopen_candidate"] is True
