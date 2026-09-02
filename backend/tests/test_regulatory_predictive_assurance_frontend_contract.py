from app.domain.regulatory_predictive_assurance import regulatory_predictive_assurance_contract

def test_release55_scope_contract():
    scope=regulatory_predictive_assurance_contract()["scope"]
    assert "scenario_analysis" in scope
    assert "assurance_forecasting" in scope
    assert "early_warning_indicators" in scope
