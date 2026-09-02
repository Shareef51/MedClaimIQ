from app.evaluation.regulatory_examination_reclosure_sustainability import sustainability_decay, repeat_recurrence_score, escalation_tier

def run_reclosure_sustainability_surveillance(items:list[dict])->dict:
    alerts=[]
    for item in items:
        decay=sustainability_decay(item)
        recurrence=repeat_recurrence_score(item.get("history",[]),item.get("cross_entity_count",0))
        tier=escalation_tier({"recurrence_count":recurrence["confirmed_occurrence_count"],"decay_score":decay["decay_score"],"affected_entity_count":item.get("cross_entity_count",1),"regulator_follow_up_overdue":item.get("regulator_follow_up_overdue",False)})
        if tier["tier"]>=2:
            alerts.append({"event":"regulatory.reclosure.repeat_recurrence_escalation","commitment_id":item.get("commitment_id"),"decay":decay,"recurrence":recurrence,"escalation":tier})
    return {"processed":len(items),"alerts":alerts,"monitoring_only":True,"worker_can_reopen":False,"worker_can_certify_effectiveness":False}
