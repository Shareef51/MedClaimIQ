from app.domain.regulatory_assurance_deficiencies import regulatory_assurance_deficiency_contract
from app.evaluation.regulatory_assurance_deficiencies import evaluate_deficiency_aggregation

def test_release58_human_authority_boundary():
    a=regulatory_assurance_deficiency_contract()["authority"]
    assert a["ai_can_declare_material_weakness"] is False
    assert a["ai_can_certify_control_effectiveness"] is False
    assert a["human_independent_escalation_required"] is True
    assert a["human_closure_required"] is True

def test_release58_traceability_evaluation():
    r=evaluate_deficiency_aggregation([{"exception_id":"e1"},{"exception_id":"e2"}],[{"exception_ids":["e1","e2"]}])
    assert r["exception_to_deficiency_traceability"]==1.0
    assert r["unlinked_exception_count"]==0
