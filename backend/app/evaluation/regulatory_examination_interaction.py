from __future__ import annotations
import hashlib, json, re
from datetime import datetime, timezone

def provenance_hash(payload:dict)->str:
    return hashlib.sha256(json.dumps(payload,sort_keys=True,default=str,separators=(",",":")).encode()).hexdigest()

def detect_commitment_candidates(statements:list[dict])->list[dict]:
    triggers=re.compile(r"\b(we will|we commit|by\s+\d{4}-\d{2}-\d{2}|deliver by|complete by|provide by)\b",re.I)
    out=[]
    for s in statements:
        text=s.get("text","")
        if triggers.search(text):
            out.append({"statement_id":s.get("statement_id"),"text":text,"candidate":True,"binding":False,"human_confirmation_required":True})
    return out

def separate_positions(items:list[dict])->dict:
    documented=[x for x in items if x.get("classification")=="documented_regulator_position"]
    interpreted=[x for x in items if x.get("classification")=="enterprise_interpretation"]
    observations=[x for x in items if x.get("classification")=="ai_observation"]
    return {"documented_regulator_positions":documented,"enterprise_interpretations":interpreted,"ai_observations":observations}

def contradiction_flags(current_statements:list[dict], prior_submissions:list[dict])->list[dict]:
    flags=[]
    prior="\n".join(x.get("text","") for x in prior_submissions).lower()
    for s in current_statements:
        text=s.get("text","").lower()
        if "complete" in text and "not complete" in prior:
            flags.append({"statement_id":s.get("statement_id"),"reason":"completion_status_conflict"})
        if "no issue" in text and "issue identified" in prior:
            flags.append({"statement_id":s.get("statement_id"),"reason":"issue_status_conflict"})
    return flags

def commitment_due_state(due_at:str|None, completed:bool=False)->dict:
    if not due_at:return {"state":"no_due_date","escalate":False}
    if completed:return {"state":"completed","escalate":False}
    due=datetime.fromisoformat(due_at.replace("Z","+00:00")); now=datetime.now(timezone.utc)
    days=(due-now).total_seconds()/86400
    if days<0:return {"state":"overdue","escalate":True,"days_remaining":int(days)}
    if days<=7:return {"state":"due_soon","escalate":True,"days_remaining":int(days)}
    return {"state":"on_track","escalate":False,"days_remaining":int(days)}
