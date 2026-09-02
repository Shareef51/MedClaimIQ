from app.domain.regulatory_closure_governance import REGULATORY_CLOSURE_AUTHORITY
from app.evaluation.regulatory_closure_governance import evaluate_closure_readiness,evaluate_traceability

def test_release60_authority_boundaries():
    assert REGULATORY_CLOSURE_AUTHORITY["ai_can_certify_remediation"] is False
    assert REGULATORY_CLOSURE_AUTHORITY["ai_can_accept_residual_risk"] is False
    assert REGULATORY_CLOSURE_AUTHORITY["ai_can_close_finding_or_issue"] is False
    assert REGULATORY_CLOSURE_AUTHORITY["worker_can_collect_or_move_money"] is False

def test_release60_readiness_requires_all_human_governed_gates():
    case={"corrective_action_refs":[{"id":"ca1"}],"retest_refs":[{"id":"rt1"}],"independent_validation_refs":[{"id":"iv1"}],"unresolved_exceptions":[],"compensating_control_exit":{"validated":True},"residual_risk":{"human_accepted":True}}
    assert evaluate_closure_readiness(case)=={"readiness_score":100,"ready":True,"closure_authority":"human_only"}

def test_release60_unresolved_exception_blocks_readiness():
    case={"corrective_action_refs":[{"id":"ca1"}],"retest_refs":[{"id":"rt1"}],"independent_validation_refs":[{"id":"iv1"}],"unresolved_exceptions":[{"id":"ex1"}],"compensating_control_exit":{"validated":True},"residual_risk":{"human_accepted":True}}
    assert evaluate_closure_readiness(case)["ready"] is False

def test_release60_traceability_chain():
    result=evaluate_traceability({"deficiency":1,"corrective_action":1,"retest":1,"independent_validation":1,"certification":1,"sustainability":1})
    assert result["passed"] is True
