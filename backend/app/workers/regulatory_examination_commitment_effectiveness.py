from app.evaluation.regulatory_examination_commitment_effectiveness import sustainability_state, recurrence_match

def run_commitment_effectiveness_watch(closed_commitments:list[dict], observations_by_commitment:dict[str,list[dict]], recurrence_signals:list[dict])->dict:
    alerts=[]
    for c in closed_commitments:
        cid=c.get("commitment_id")
        state=sustainability_state(observations_by_commitment.get(cid,[]),c.get("minimum_sustainability_days",30))
        if state.get("reopen_candidate"):
            alerts.append({"event":"regulatory.commitment_effectiveness.sustainability_at_risk","commitment_id":cid,"state":state})
        matches=recurrence_match(c,recurrence_signals)
        if matches:
            alerts.append({"event":"regulatory.commitment_effectiveness.recurrence_candidate","commitment_id":cid,"matches":matches})
    return {"checked":len(closed_commitments),"alerts":alerts,"monitoring_only":True,"worker_can_certify_closure":False,"worker_can_reopen":False}
