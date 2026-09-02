from app.evaluation.regulatory_predictive_assurance import evaluate_predictive_forecast

def test_mae_is_deterministic():
    p={"remediation_failure_risk":10,"deadline_breach_risk":20,"recurrence_risk":30,"control_deterioration_risk":40}
    a={"remediation_failure_risk":20,"deadline_breach_risk":30,"recurrence_risk":40,"control_deterioration_risk":50}
    assert evaluate_predictive_forecast(p,a)["mae"]==10
