from __future__ import annotations
import hashlib, json

def version_hash(payload:dict)->str:
    return hashlib.sha256(json.dumps(payload,sort_keys=True,default=str,separators=(",",":")).encode()).hexdigest()

def sustainability_decay(payload:dict)->dict:
    baseline=float(payload.get("baseline_control_health",100)); current=float(payload.get("current_control_health",baseline))
    days=int(payload.get("days_since_reclosure",0)); stale=int(payload.get("stale_evidence_count",0)); failed=int(payload.get("failed_observation_count",0))
    health_drop=max(0.0,baseline-current)
    score=min(100, round(health_drop*0.55 + min(days/365*20,20) + stale*5 + failed*12,2))
    level="critical" if score>=75 else "high" if score>=50 else "moderate" if score>=25 else "low"
    return {"decay_score":score,"risk_level":level,"control_health_drop":round(health_drop,2),"human_review_required":score>=25}

def repeat_recurrence_score(history:list[dict], cross_entity_count:int=0)->dict:
    confirmed=[x for x in history if x.get("confirmed",True) and x.get("event_type") in {"recurrence","reopened","control_failure","reclosure_failure"}]
    count=len(confirmed)
    third=count>=3
    score=min(100, count*25 + min(int(cross_entity_count),5)*8)
    return {"confirmed_occurrence_count":count,"repeat_recurrence_score":score,"third_occurrence":third,"systemic_pattern_candidate":third or int(cross_entity_count)>=3,"mandatory_executive_review":third,"mandatory_internal_audit_review":third}

def escalation_tier(payload:dict)->dict:
    recurrence=int(payload.get("recurrence_count",0)); decay=float(payload.get("decay_score",0)); entities=int(payload.get("affected_entity_count",1)); regulator_follow_up=bool(payload.get("regulator_follow_up_overdue",False))
    points=recurrence*20 + (25 if decay>=50 else 10 if decay>=25 else 0) + min(entities,5)*5 + (20 if regulator_follow_up else 0)
    tier=4 if points>=90 else 3 if points>=65 else 2 if points>=40 else 1
    return {"tier":tier,"score":min(points,100),"executive_review_required":tier>=3,"internal_audit_review_required":recurrence>=3 or tier==4,"human_investigation_required":tier>=2}

def compare_reclosures(prior:dict,current:dict)->dict:
    prior_health=float(prior.get("control_health",0)); current_health=float(current.get("control_health",0))
    return {"control_health_delta":round(current_health-prior_health,2),"same_root_cause":prior.get("root_cause_id") is not None and prior.get("root_cause_id")==current.get("root_cause_id"),"same_control":prior.get("control_id") is not None and prior.get("control_id")==current.get("control_id"),"human_interpretation_required":True}
