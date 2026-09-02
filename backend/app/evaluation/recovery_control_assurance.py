from __future__ import annotations
import json
from pathlib import Path

def evaluate(path:Path)->dict:
    data=json.loads(path.read_text());cases=data.get("cases",[]);passed=sum(1 for x in cases if x.get("expected") and x.get("authority_violation") is False)
    return {"cases":len(cases),"passed":passed,"pass_rate":0 if not cases else round(passed/len(cases),4),"authority_violations":sum(1 for x in cases if x.get("authority_violation"))}
