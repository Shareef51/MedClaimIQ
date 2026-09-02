from app.evaluation.regulatory_examination_systemic_recurrence_portfolio import aggregate_systemic_patterns, supervisory_materiality_score

def run_systemic_recurrence_portfolio_monitor(items:list[dict])->dict:
    alerts=[]
    for item in items:
        agg=aggregate_systemic_patterns(item.get("occurrences",[]))
        score=supervisory_materiality_score({**item.get("materiality_inputs",{}),"recurring_commitment_count":agg["recurring_commitment_count"],"affected_entity_count":agg["affected_entity_count"],"affected_examination_count":agg["affected_examination_count"]})
        if agg["systemic_pattern_candidate"] or score["enterprise_intervention_required"]:
            alerts.append({"portfolio_id":item.get("portfolio_id"),"event":"regulatory.systemic_recurrence.enterprise_review_required","assessment":agg,"materiality":score,"monitoring_only":True,"human_action_required":True})
    return {"processed":len(items),"alerts":alerts,"worker_can_approve_intervention":False,"worker_can_close_commitments":False}
