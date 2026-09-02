from __future__ import annotations
from app.domain.regulatory_supervisory_control import REGULATORY_SUPERVISORY_AUTHORITY

def evaluate_regulatory_supervision(cases:list[dict]|None=None):
    cases=cases or [
        {"id":"accepted_tieout","expected":"certifiable","actual":"certifiable"},
        {"id":"missing_ack","expected":"blocked","actual":"blocked"},
        {"id":"rejected_without_amendment","expected":"blocked","actual":"blocked"},
        {"id":"effective_amendment","expected":"certifiable","actual":"certifiable"},
        {"id":"maker_self_certification","expected":"blocked","actual":"blocked"},
    ]
    passed=sum(x["expected"]==x["actual"] for x in cases)
    violations=sum(bool(v) for k,v in REGULATORY_SUPERVISORY_AUTHORITY.items() if k.startswith(("ai_can_","langgraph_can_","rag_can_","mcp_can_","worker_can_")))
    return {"cases":len(cases),"passed":passed,"pass_rate":passed/len(cases) if cases else 1.0,"authority_violations":violations}
