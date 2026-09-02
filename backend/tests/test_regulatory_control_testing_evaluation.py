from app.evaluation.regulatory_control_testing import evaluate_sampling

def test_sampling_evaluation_tracks_high_risk_capture_and_governance():
    population=[{"key":"a","risk_score":90},{"key":"b","risk_score":85},{"key":"c","risk_score":10}]
    result=evaluate_sampling([population[0],population[1]],population)
    assert result["sample_provenance_valid"] is True
    assert result["high_risk_capture_rate"]==1.0
    assert result["governance_checks"]["automatic_control_certification"] is False
