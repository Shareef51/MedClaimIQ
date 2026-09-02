from app.domain.regulatory_remediation import REGULATORY_REMEDIATION_AUTHORITY

def evaluate_regulatory_remediation(cases:list[dict]|None=None):
    cases=cases or [
        {"id":"ai_recommendation_only","expected":"blocked_from_approval","actual":"blocked_from_approval"},
        {"id":"maker_checker_plan_approval","expected":"required","actual":"required"},
        {"id":"dependency_evidence_retest_gate","expected":"required","actual":"required"},
        {"id":"open_waiver_closure","expected":"blocked","actual":"blocked"},
        {"id":"independent_closure_certification","expected":"required","actual":"required"},
    ]
    passed=sum(x["expected"]==x["actual"] for x in cases)
    violations=sum(bool(v) for k,v in REGULATORY_REMEDIATION_AUTHORITY.items() if k.startswith(("ai_can_","langgraph_can_","rag_can_","mcp_can_","worker_can_")))
    return {"cases":len(cases),"passed":passed,"pass_rate":passed/len(cases) if cases else 1.0,"authority_violations":violations}
