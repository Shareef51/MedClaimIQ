from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone

def version_hash(payload:dict)->str:
    return hashlib.sha256(json.dumps(payload,sort_keys=True,default=str,separators=(",",":")).encode()).hexdigest()

def due_state(due_at:str|None, completed:bool=False, warning_days:int=14)->dict:
    if not due_at:return {"state":"no_due_date","escalate":False}
    if completed:return {"state":"completed","escalate":False}
    due=datetime.fromisoformat(due_at.replace("Z","+00:00")); now=datetime.now(timezone.utc)
    days=(due-now).total_seconds()/86400
    if days<0:return {"state":"overdue","escalate":True,"days_remaining":int(days)}
    if days<=warning_days:return {"state":"due_soon","escalate":True,"days_remaining":int(days)}
    return {"state":"on_track","escalate":False,"days_remaining":int(days)}

def reconciliation_flags(commitment:dict,written_records:list[dict])->list[dict]:
    flags=[]; desc=(commitment.get("description") or "").strip().lower(); due=commitment.get("due_at")
    for w in written_records:
        if w.get("commitment_id")==commitment.get("commitment_id"):
            if (w.get("description") or "").strip().lower()!=desc: flags.append({"type":"description_mismatch","written_ref":w.get("reference")})
            if w.get("due_at") and due and w.get("due_at")!=due: flags.append({"type":"due_date_mismatch","written_ref":w.get("reference")})
    return flags

def completion_readiness(commitment:dict,milestones:list[dict],evidence:list[dict],validations:list[dict])->dict:
    blockers=[]
    if not milestones: blockers.append("milestones_missing")
    elif any(m.get("status")!="completed" for m in milestones): blockers.append("milestones_incomplete")
    required=set(commitment.get("required_evidence_types",[])); supplied={e.get("evidence_type") for e in evidence if e.get("status","active")=="active"}
    missing=sorted(required-supplied)
    if missing: blockers.append("required_evidence_missing:"+",".join(missing))
    if not validations or any(v.get("result")!="effective" for v in validations): blockers.append("effectiveness_validation_incomplete")
    return {"ready":not blockers,"blockers":blockers,"human_certification_required":True,"automated_certification_allowed":False}

def cross_examination_clusters(commitments:list[dict])->list[dict]:
    groups={}
    for c in commitments:
        key=(c.get("control_id"),c.get("obligation_id"),c.get("normalized_theme"))
        if any(key): groups.setdefault(key,[]).append(c)
    return [{"control_id":k[0],"obligation_id":k[1],"theme":k[2],"commitment_ids":[x.get("commitment_id") for x in v],"examination_ids":sorted({x.get("examination_id") for x in v if x.get("examination_id")}),"cross_examination":len({x.get("examination_id") for x in v if x.get("examination_id")})>1} for k,v in groups.items() if len(v)>1]
