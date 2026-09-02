from app.domain.regulatory_predictive_assurance import regulatory_predictive_assurance_contract
from app.evaluation.regulatory_predictive_assurance import evaluate_predictive_forecast

def test_authority_is_prediction_only():
    a=regulatory_predictive_assurance_contract()["authority"]
    assert a["ai_prediction_only"] is True
    assert a["ai_can_approve_remediation"] is False
    assert a["ai_can_accept_residual_risk"] is False
    assert a["ai_can_certify_controls"] is False
    assert a["ai_can_close_findings"] is False
    assert a["fund_movement"] is False

def test_predictive_evaluation_has_governance():
    r=evaluate_predictive_forecast({"remediation_failure_risk":70},{"remediation_failure_risk":80})
    assert r["governance_checks"]["human_review_required"] is True
    assert r["governance_checks"]["automatic_regulatory_action"] is False
