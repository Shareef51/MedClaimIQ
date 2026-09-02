from app.evaluation.regulatory_examination_reopened_commitment_reclosure import reclosure_readiness, second_recurrence_assessment

def run_reopened_commitment_assurance(commitments:list[dict])->dict:
    alerts=[]
    for item in commitments:
        cid=item.get("commitment_id")
        recurrence=second_recurrence_assessment(item.get("history",[]))
        if recurrence["second_recurrence"]:
            alerts.append({"event":"regulatory.reopened_commitment.second_recurrence_escalation","commitment_id":cid,"assessment":recurrence})
        readiness=reclosure_readiness(item.get("readiness",{}))
        if readiness["ready"]:
            alerts.append({"event":"regulatory.reopened_commitment.ready_for_human_recertification","commitment_id":cid,"readiness":readiness})
    return {"alerts":alerts,"processed":len(commitments),"monitoring_only":True,"worker_can_reclose":False}
