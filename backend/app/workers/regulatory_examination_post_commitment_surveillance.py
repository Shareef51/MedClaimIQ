from app.evaluation.regulatory_examination_post_commitment_surveillance import sustainability_decay, match_new_examination, cross_entity_recurrence

def run_post_commitment_surveillance(closed_commitments:list[dict], observations_by_commitment:dict[str,list[dict]], new_findings:list[dict], cross_entity_signals:list[dict])->dict:
    alerts=[]
    for commitment in closed_commitments:
        cid=commitment.get("commitment_id")
        decay=sustainability_decay(observations_by_commitment.get(cid,[]))
        if decay.get("reopen_candidate"):
            alerts.append({"event":"regulatory.post_commitment.sustainability_decay","commitment_id":cid,"assessment":decay})
        matches=match_new_examination(commitment,new_findings)
        if matches:
            alerts.append({"event":"regulatory.post_commitment.examination_recurrence_candidate","commitment_id":cid,"matches":matches})
    propagation=cross_entity_recurrence(cross_entity_signals)
    if propagation.get("candidate"):
        alerts.append({"event":"regulatory.post_commitment.cross_entity_recurrence","assessment":propagation})
    return {"checked":len(closed_commitments),"alerts":alerts,"monitoring_only":True,"worker_can_reopen":False,"worker_can_certify_effectiveness":False}
