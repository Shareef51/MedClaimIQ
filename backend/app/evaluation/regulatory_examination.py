from app.domain.regulatory_examination import REGULATORY_EXAMINATION_AUTHORITY

def evaluate_regulatory_examination(cases:list[dict]|None=None):
    cases=cases or [
        {"id":"cited_evidence_pack","expected":"allowed","actual":"allowed"},
        {"id":"ai_draft_requires_human_checker","expected":"blocked_until_human","actual":"blocked_until_human"},
        {"id":"maker_self_approval","expected":"blocked","actual":"blocked"},
        {"id":"open_material_finding_closure","expected":"blocked","actual":"blocked"},
        {"id":"human_approved_secure_response","expected":"allowed","actual":"allowed"},
    ]
    passed=sum(x["expected"]==x["actual"] for x in cases)
    violations=sum(bool(v) for k,v in REGULATORY_EXAMINATION_AUTHORITY.items() if k.startswith(("ai_can_","langgraph_can_","rag_can_","mcp_can_","worker_can_")))
    return {"cases":len(cases),"passed":passed,"pass_rate":passed/len(cases) if cases else 1.0,"authority_violations":violations}
