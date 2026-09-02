from app.domain.regulatory_control_testing import regulatory_control_testing_contract
from app.services.regulatory_control_testing import RegulatoryControlTestingService

def test_release57_authority_requires_human_independent_conclusion():
    a=regulatory_control_testing_contract()["authority"]
    assert a["orchestration_only"] is True
    assert a["ai_can_conclude_control_effectiveness"] is False
    assert a["ai_can_certify_controls"] is False
    assert a["ai_can_approve_remediation"] is False
    assert a["ai_can_accept_residual_risk"] is False
    assert a["ai_can_close_findings"] is False
    assert a["human_independent_conclusion_required"] is True

def test_risk_based_sampling_is_deterministic_and_prioritizes_risk():
    population=[{"key":"a","risk_score":20},{"key":"b","risk_score":99},{"key":"c","risk_score":80},{"key":"d","risk_score":5}]
    s=RegulatoryControlTestingService.select_risk_based_sample(population,2)
    assert [x["key"] for x in s]==["b","c"]
