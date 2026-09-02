from __future__ import annotations

def evaluate_financial_investigation_cases(cases:list[dict])->dict:
    passed=0;violations=0;details=[]
    for case in cases:
        expected=case.get("expected_controls",{});authority=case.get("authority",{})
        ok=bool(expected.get("human_investigator_required",True) and expected.get("immutable_evidence_pack",True) and expected.get("material_dual_approval",True))
        if authority.get("ai_can_execute_remediation") or authority.get("automation_can_move_funds"):violations+=1;ok=False
        passed+=int(ok);details.append({"case_id":case.get("case_id"),"passed":ok})
    return {"cases":len(cases),"passed":passed,"pass_rate":0 if not cases else passed/len(cases),"authority_violations":violations,"details":details}
