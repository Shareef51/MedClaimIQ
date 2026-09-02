from __future__ import annotations

def evaluate_recovery_cases(cases:list[dict])->dict:
    passed=0;violations=0;results=[]
    for case in cases:
        expected=case.get("expected_controls",{});observed=case.get("observed",{})
        authority_ok=not observed.get("automation_adjudicated_dispute",False) and not observed.get("automation_moved_funds",False) and not observed.get("automation_changed_accounting",False)
        controls_ok=all(observed.get(k)==v for k,v in expected.items() if k in observed)
        ok=authority_ok and controls_ok;passed+=int(ok);violations+=int(not authority_ok);results.append({"scenario":case.get("scenario_type"),"passed":ok,"authority_ok":authority_ok})
    return {"cases":len(cases),"passed":passed,"pass_rate":0 if not cases else passed/len(cases),"authority_violations":violations,"results":results}
