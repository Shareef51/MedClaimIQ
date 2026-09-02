from __future__ import annotations
import json
from pathlib import Path
def evaluate_dataset(path:Path)->dict[str,object]:
    cases=json.loads(path.read_text());passed=0;authority_violations=0;details=[]
    for c in cases:
        blocked=(not c["citations"]) or (not c["resolved_policy_conflicts"]) or (c["material"] and not c["second_review"])
        observed="blocked" if blocked else ("pending_human_accounting_referral" if c["case_key"]=="reversal-referral" else "closable")
        ok=observed==c["expected"] and c.get("requires_human_resolution") is True
        passed+=int(ok);authority_violations+=int(c.get("requires_human_resolution") is not True);details.append({"case_key":c["case_key"],"expected":c["expected"],"observed":observed,"passed":ok})
    return {"cases":len(cases),"passed":passed,"pass_rate":0 if not cases else passed/len(cases),"authority_violations":authority_violations,"details":details}
