from __future__ import annotations
import json
from pathlib import Path

def evaluate_financial_intelligence_dataset(path: str | Path) -> dict:
    cases=json.loads(Path(path).read_text())
    results=[]
    for case in cases:
        checks={
            "read_only_required":case.get("expected_authority")=="none",
            "citations_required":bool(case.get("required_citation_types")),
            "expected_signal_present":bool(case.get("expected_signal")),
            "human_action_required":case.get("requires_human_finance_action",True),
        }
        results.append({"case_id":case["case_id"],"passed":all(checks.values()),"checks":checks})
    passed=sum(1 for x in results if x["passed"])
    return {"cases":len(results),"passed":passed,"pass_rate":0 if not results else round(passed/len(results),4),"authority_violations":sum(1 for x in results if not x["checks"]["read_only_required"]),"results":results}
