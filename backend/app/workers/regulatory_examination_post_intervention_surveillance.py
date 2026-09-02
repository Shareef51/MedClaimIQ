from app.evaluation.regulatory_examination_post_intervention_surveillance import systemic_recurrence_signal

def run_post_intervention_surveillance_monitor(items:list[dict])->dict:
    alerts=[]
    for item in items:
        signal=systemic_recurrence_signal(item)
        if signal["reopen_candidate"]:
            alerts.append({"intervention_program_id":item.get("intervention_program_id"),"event":"regulatory.enterprise_intervention.systemic_recurrence_attention_required","signal":signal,"monitoring_only":True,"human_investigation_required":True})
    return {"processed":len(items),"alerts":alerts,"worker_can_reopen_intervention_program":False,"worker_can_certify_effectiveness":False,"worker_can_accept_residual_systemic_risk":False}
