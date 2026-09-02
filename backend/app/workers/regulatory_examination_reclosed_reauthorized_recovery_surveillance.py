from app.evaluation.regulatory_examination_reclosed_reauthorized_recovery_surveillance import repeated_recovery_decay,systemic_risk_rebound,cross_entity_recurrence,examination_finding_correlation,regulator_followup_linkage

def run_reclosed_reauthorized_recovery_surveillance_monitor(items:list[dict])->dict:
    alerts=[]
    for item in items:
        decay=repeated_recovery_decay(item); rebound=systemic_risk_rebound(item); recurrence=cross_entity_recurrence(item)
        findings=examination_finding_correlation(item); followups=regulator_followup_linkage(item)
        if decay["human_investigation_required"] or rebound["material_rebound_candidate"] or recurrence["cross_entity_recurrence_propagation"] or findings["new_examination_finding_correlation"] or followups["regulator_followup_escalation_candidate"]:
            alerts.append({"recovery_program_id":item.get("recovery_program_id"),"human_review_required":True,"repeated_recovery_decay_score":decay["repeated_recovery_decay_score"],"material_rebound_candidate":rebound["material_rebound_candidate"],"cross_entity_recurrence_propagation":recurrence["cross_entity_recurrence_propagation"],"matched_item_count":findings["matched_item_count"],"regulator_followup_escalation_candidate":followups["regulator_followup_escalation_candidate"]})
    return {"monitoring_only":True,"automated_investigation_opening":False,"automated_reopening":False,"automated_recovery_certification":False,"automated_risk_acceptance":False,"alerts":alerts}
