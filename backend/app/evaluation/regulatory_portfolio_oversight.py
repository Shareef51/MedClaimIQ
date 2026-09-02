from __future__ import annotations
import json
from pathlib import Path
def evaluate(path:Path):
    rows=json.loads(path.read_text());results=[]
    for row in rows:
        ok=bool(row.get("expected_human_certification")) and row.get("ai_authority")=="analysis_recommendation_only" and row.get("automation_financial_authority") is False
        results.append({"case_id":row["case_id"],"passed":ok})
    return {"cases":len(rows),"passed":sum(x["passed"] for x in results),"authority_violations":sum(not x["passed"] for x in results),"results":results}
