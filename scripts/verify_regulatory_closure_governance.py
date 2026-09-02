from app.domain.regulatory_closure_governance import REGULATORY_CLOSURE_AUTHORITY
from app.evaluation.regulatory_closure_governance import evaluate_closure_readiness

def main():
    assert REGULATORY_CLOSURE_AUTHORITY["ai_can_certify_remediation"] is False
    assert REGULATORY_CLOSURE_AUTHORITY["ai_can_accept_residual_risk"] is False
    assert REGULATORY_CLOSURE_AUTHORITY["ai_can_close_finding_or_issue"] is False
    r=evaluate_closure_readiness({"corrective_action_refs":[1],"retest_refs":[1],"independent_validation_refs":[1],"unresolved_exceptions":[],"compensating_control_exit":{"validated":True},"residual_risk":{"human_accepted":True}})
    assert r["ready"] is True and r["readiness_score"] == 100
    print("Release 60 regulatory closure governance verification passed")
if __name__=="__main__": main()
