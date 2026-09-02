from app.evaluation.regulatory_examination_reclosed_intervention_sustainability import sustainability_health, multi_cycle_recurrence, cross_entity_propagation

def run_reclosed_intervention_sustainability_monitor(items:list[dict])->dict:
    alerts=[]
    for item in items:
        health=sustainability_health(item)
        recurrence=multi_cycle_recurrence(item)
        propagation=cross_entity_propagation(item)
        if health["sustainability_at_risk"] or recurrence["repeated_systemic_failure"] or propagation["enterprise_propagation"]:
            alerts.append({"intervention_program_id":item.get("intervention_program_id"),"sustainability_at_risk":health["sustainability_at_risk"],"multi_cycle_recurrence_score":recurrence["multi_cycle_recurrence_score"],"enterprise_propagation":propagation["enterprise_propagation"],"executive_review_required":recurrence["executive_review_required"],"internal_audit_review_required":recurrence["internal_audit_review_required"],"human_review_required":True,"worker_action_authority":False})
    return {"monitoring_only":True,"automated_reopening":False,"automated_reclosure":False,"automated_risk_acceptance":False,"automated_effectiveness_certification":False,"alerts":alerts}
