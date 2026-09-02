from app.domain.regulatory_continuous_assurance import regulatory_continuous_assurance_contract

def test_release56_scope_contract():
    scope=regulatory_continuous_assurance_contract()["scope"]
    assert "control_drift_detection" in scope
    assert "forecast_vs_actual_tracking" in scope
    assert "supervisory_early_warning" in scope
    assert "evidence_freshness_checks" in scope
    assert "sse_operational_events" in scope
