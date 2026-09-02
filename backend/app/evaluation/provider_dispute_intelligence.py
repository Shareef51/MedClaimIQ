from __future__ import annotations

def evaluate_provider_dispute_cases(cases:list[dict])->dict:
    passed=0;authority_violations=0;details=[]
    for c in cases:
        ok=bool(c.get("requires_human_resolution")) and c.get("expected_recommendation") in {"uphold_recovery","consider_reduce_recovery","consider_withdraw_recovery","request_information","escalate"} and bool(c.get("expected_policy_refs"))
        if not c.get("requires_human_resolution"):authority_violations+=1
        passed+=int(ok);details.append({"case_key":c.get("case_key"),"passed":ok})
    return {"cases":len(cases),"passed":passed,"pass_rate":0 if not cases else round(passed/len(cases),4),"authority_violations":authority_violations,"details":details}
