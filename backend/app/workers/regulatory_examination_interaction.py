from app.evaluation.regulatory_examination_interaction import commitment_due_state

def run_interaction_watch(commitments:list[dict])->dict:
    alerts=[]
    for c in commitments:
        state=commitment_due_state(c.get("due_at"),c.get("status")=="completed")
        if state.get("escalate"):
            alerts.append({"event":"regulatory.interaction.commitment_at_risk","commitment_id":c.get("commitment_id"),"state":state})
    return {"checked":len(commitments),"alerts":alerts,"monitoring_only":True,"worker_can_confirm_commitment":False}
