from app.evaluation.regulatory_examination_enterprise_intervention_execution import program_execution_readiness, resource_capacity_risk

def run_enterprise_intervention_execution_monitor(items:list[dict])->dict:
    alerts=[]
    for item in items:
        readiness=program_execution_readiness(item)
        capacity=resource_capacity_risk(item.get("capacity",{}))
        if readiness["blockers"] or capacity["executive_attention_required"]:
            alerts.append({"intervention_program_id":item.get("intervention_program_id"),"event":"regulatory.enterprise_intervention.executive_attention_required","readiness":readiness,"capacity":capacity,"monitoring_only":True,"human_action_required":True})
    return {"processed":len(items),"alerts":alerts,"worker_can_approve_program":False,"worker_can_certify_effectiveness":False,"worker_can_accept_residual_risk":False}
