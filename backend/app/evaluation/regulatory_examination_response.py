from __future__ import annotations
from hashlib import sha256
import json

def evidence_refresh_status(evidence: list[dict], current_versions: dict[str,str]) -> dict:
    stale=[]; missing=[]
    for item in evidence:
        eid=item.get("evidence_id")
        if not eid: continue
        current=current_versions.get(eid)
        if current is None: missing.append(eid)
        elif str(item.get("version")) != str(current): stale.append(eid)
    return {"fresh": not stale and not missing, "stale_evidence_ids":sorted(stale), "missing_evidence_ids":sorted(missing)}

def detect_response_contradictions(current_text: str, prior_responses: list[dict]) -> list[dict]:
    # Deterministic contract: explicit structured facts are compared; LLM may only suggest additional candidates.
    out=[]
    current_facts={x.strip().lower() for x in current_text.split(";") if "=" in x}
    current_keys={x.split("=",1)[0].strip():x.split("=",1)[1].strip() for x in current_facts}
    for prior in prior_responses:
        facts={x.strip().lower() for x in str(prior.get("text","")).split(";") if "=" in x}
        for fact in facts:
            k,v=fact.split("=",1)
            if k.strip() in current_keys and current_keys[k.strip()] != v.strip():
                out.append({"prior_response_id":prior.get("response_id"),"field":k.strip(),"prior":v.strip(),"current":current_keys[k.strip()]})
    return out

def sla_risk(due_in_hours: float, unresolved_dependencies: int=0, review_pending: bool=False) -> dict:
    score=0
    if due_in_hours <= 0: score += 70
    elif due_in_hours <= 24: score += 45
    elif due_in_hours <= 72: score += 25
    if unresolved_dependencies: score += min(20, unresolved_dependencies*5)
    if review_pending: score += 15
    score=min(100,score)
    return {"score":score,"level":"critical" if score>=80 else "high" if score>=60 else "moderate" if score>=30 else "low"}

def immutable_revision_hash(payload: dict) -> str:
    canonical=json.dumps(payload,sort_keys=True,separators=(",",":"),default=str)
    return sha256(canonical.encode()).hexdigest()

def reconciliation_status(submission: dict, receipt: dict|None, followups: list[dict]) -> dict:
    if not submission.get("human_approved"):
        return {"reconciled":False,"blockers":["submission_not_human_approved"]}
    blockers=[]
    if not receipt: blockers.append("submission_receipt_missing")
    elif receipt.get("status") not in {"received","acknowledged"}: blockers.append("receipt_not_acknowledged")
    if any(f.get("status") not in {"resolved","closed"} for f in followups): blockers.append("open_follow_up")
    return {"reconciled":not blockers,"blockers":blockers}
