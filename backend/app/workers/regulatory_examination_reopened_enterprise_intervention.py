from app.evaluation.regulatory_examination_reopened_enterprise_intervention import second_systemic_recurrence, propagation_readiness

def run_reopened_enterprise_intervention_monitor(items:list[dict])->dict:
    alerts=[]
    for item in items:
        recurrence=second_systemic_recurrence(item.get("history",[]))
        propagation=propagation_readiness(item)
        if recurrence["second_systemic_recurrence"] or not propagation["cross_entity_propagation_complete"]:
            alerts.append({"intervention_program_id":item.get("intervention_program_id"),"second_systemic_recurrence":recurrence["second_systemic_recurrence"],"missing_entity_ids":propagation["missing_entity_ids"],"human_review_required":True,"worker_action_authority":False})
    return {"monitoring_only":True,"automated_approval":False,"automated_risk_acceptance":False,"automated_reclosure":False,"alerts":alerts}
