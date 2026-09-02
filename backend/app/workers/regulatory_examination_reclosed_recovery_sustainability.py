from app.evaluation.regulatory_examination_reclosed_recovery_sustainability import recovery_decay_score,multi_cycle_recurrence,risk_rebound_correlation,regulator_followup_correlation,enterprise_materiality
def run_reclosed_recovery_sustainability_monitor(items:list[dict])->dict:
    alerts=[]
    for item in items:
        decay=recovery_decay_score(item); recur=multi_cycle_recurrence(item); rebound=risk_rebound_correlation(item); regulator=regulator_followup_correlation(item)
        materiality=enterprise_materiality({**item,**decay,**recur,**rebound,**regulator,"affected_entity_count":len(recur["affected_entity_ids"])})
        if materiality["human_investigation_required"] or recur["multi_cycle_recurrence"]:
            alerts.append({"intervention_program_id":item.get("intervention_program_id"),**decay,**recur,**rebound,**regulator,**materiality,"human_review_required":True})
    return {"monitoring_only":True,"automated_investigation_opening":False,"automated_program_reopening":False,"automated_risk_acceptance":False,"automated_recovery_certification":False,"alerts":alerts}
