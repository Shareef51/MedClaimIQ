from app.domain.regulatory_deficiency_lifecycle import regulatory_deficiency_lifecycle_contract
from app.evaluation.regulatory_deficiency_lifecycle import evaluate_lifecycle_traceability

def test_release59_human_authority_boundary():
    a=regulatory_deficiency_lifecycle_contract()["authority"]
    assert a["ai_can_formally_classify_material_weakness"] is False
    assert a["ai_can_approve_corrective_action"] is False
    assert a["ai_can_close_enterprise_issue"] is False
    assert a["executive_human_attestation_required"] is True

def test_release59_end_to_end_traceability_metric():
    x=evaluate_lifecycle_traceability([{"deficiency_key":"D1"}],[{"deficiency_key":"D1"}],[{"deficiency_key":"D1"}])
    assert x["investigation_to_attestation_traceability"]==1.0
    assert x["untraced_deficiency_count"]==0
