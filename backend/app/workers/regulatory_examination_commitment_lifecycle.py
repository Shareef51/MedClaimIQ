from app.evaluation.regulatory_examination_commitment_lifecycle import due_state

def run_commitment_lifecycle_watch(commitments:list[dict],milestones:list[dict],follow_ups:list[dict])->dict:
    alerts=[]
    for kind,items,id_key in (("commitment",commitments,"commitment_id"),("milestone",milestones,"milestone_id"),("follow_up",follow_ups,"follow_up_id")):
        for item in items:
            state=due_state(item.get("due_at"),item.get("status") in {"completed","closed","acknowledged"})
            if state.get("escalate"):
                alerts.append({"event":f"regulatory.commitment_lifecycle.{kind}_at_risk",id_key:item.get(id_key),"state":state})
    return {"checked":len(commitments)+len(milestones)+len(follow_ups),"alerts":alerts,"monitoring_only":True,"worker_can_certify_completion":False}
