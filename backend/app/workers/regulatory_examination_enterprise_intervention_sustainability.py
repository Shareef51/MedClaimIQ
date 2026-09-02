from app.evaluation.regulatory_examination_enterprise_intervention_sustainability import sustainability_assurance, recurrence_reopen_signal

def run_enterprise_intervention_sustainability_monitor(items:list[dict])->dict:
    alerts=[]
    for item in items:
        assurance=sustainability_assurance(item)
        recurrence=recurrence_reopen_signal(item)
        if not assurance["eligible_for_human_closure_review"] or recurrence["reopen_candidate"]:
            alerts.append({"intervention_program_id":item.get("intervention_program_id"),"event":"regulatory.enterprise_intervention.sustainability_attention_required","assurance":assurance,"recurrence":recurrence,"monitoring_only":True,"human_action_required":True})
    return {"processed":len(items),"alerts":alerts,"worker_can_accept_residual_risk":False,"worker_can_close_intervention_program":False,"worker_can_certify_sustainability":False}
