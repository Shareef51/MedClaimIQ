from app.domain.regulatory_continuous_assurance import regulatory_continuous_assurance_contract
from app.services.regulatory_continuous_assurance import RegulatoryContinuousAssuranceService

def test_release56_authority_is_monitoring_only():
    a=regulatory_continuous_assurance_contract()["authority"]
    assert a["monitoring_only"] is True
    assert a["ai_can_approve_remediation"] is False
    assert a["ai_can_accept_residual_risk"] is False
    assert a["ai_can_certify_controls"] is False
    assert a["ai_can_close_findings"] is False
    assert a["worker_can_execute_corrective_actions"] is False
    assert a["fund_movement"] is False

def test_drift_scoring_escalates_material_gap():
    low=RegulatoryContinuousAssuranceService.drift_score(observed_value=78,expected_value=80,evidence_age_days=3,signal_type="control_health")
    high=RegulatoryContinuousAssuranceService.drift_score(observed_value=25,expected_value=90,evidence_age_days=45,signal_type="control_test_failure")
    assert high>low
    assert RegulatoryContinuousAssuranceService.severity(high) in {"high","critical"}
