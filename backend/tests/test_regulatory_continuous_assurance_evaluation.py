from app.evaluation.regulatory_continuous_assurance import evaluate_drift_detection

def test_drift_evaluation_tracks_false_positive_and_governance():
    r=evaluate_drift_detection([{"key":"c1","severity":"high"},{"key":"c2","severity":"critical"}],[{"key":"c1","severity":"high"}])
    assert r["precision"]==0.5
    assert r["false_positive_count"]==1
    assert r["governance_checks"]["human_investigation_required_for_material_drift"] is True
    assert r["governance_checks"]["automatic_corrective_action"] is False
