from __future__ import annotations
import hashlib, json

def version_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()

def recovery_decay_score(payload: dict) -> dict:
    baseline=float(payload.get("baseline_control_health_score",100) or 100)
    current=float(payload.get("current_control_health_score",baseline) or baseline)
    failed=int(payload.get("failed_observation_count",0) or 0)
    stale=int(payload.get("stale_evidence_count",0) or 0)
    breaches=int(payload.get("sustainability_breach_count",0) or 0)
    days=int(payload.get("days_since_reclosure",0) or 0)
    health_decay=max(0.0, baseline-current)
    score=min(100.0, round(health_decay*0.9 + failed*12 + stale*5 + breaches*15 + min(days/30,12)*1.5,2))
    level="critical" if score>=75 else "high" if score>=50 else "moderate" if score>=25 else "low"
    return {"recovery_decay_score":score,"decay_risk_level":level,"health_delta":round(current-baseline,2),"human_review_required":score>=25}

def multi_cycle_recurrence(payload: dict) -> dict:
    cycles=payload.get("cycles",[])
    failure_states={"failed","recurred","reopened","degraded","sustainability_breach","control_failure"}
    failed=[c for c in cycles if str(c.get("status","")).lower() in failure_states or bool(c.get("recovery_failure"))]
    root_causes=[str(c.get("root_cause_id")) for c in failed if c.get("root_cause_id")]
    controls=[str(c.get("control_id")) for c in failed if c.get("control_id")]
    entities=sorted({str(e) for c in failed for e in c.get("entity_ids",[]) if e})
    repeated_root=bool(root_causes) and len(set(root_causes)) < len(root_causes)
    repeated_control=bool(controls) and len(set(controls)) < len(controls)
    count=len(failed)
    systemic=count>=2 and (repeated_root or repeated_control or len(entities)>=3)
    return {"cycle_count":len(cycles),"failed_cycle_count":count,"affected_entity_ids":entities,"repeated_root_cause":repeated_root,"repeated_control_failure":repeated_control,"multi_cycle_recurrence":count>=2,"systemic_recovery_failure_candidate":systemic,"executive_internal_audit_challenge_required":count>=2}

def risk_rebound_correlation(payload: dict) -> dict:
    points=payload.get("risk_history",[])
    if not points: return {"risk_rebound_detected":False,"peak_rebound":0.0,"trajectory":"unknown"}
    baseline=float(payload.get("reclosure_risk_score",points[0].get("score",0)) or 0)
    vals=[float(x.get("score",0) or 0) for x in points]
    peak=max(vals)
    rebound=peak>baseline
    trajectory="worsening" if vals[-1]>vals[0] else "improving" if vals[-1]<vals[0] else "flat"
    return {"risk_rebound_detected":rebound,"reclosure_risk_score":baseline,"peak_risk_score":peak,"peak_rebound":round(max(0,peak-baseline),2),"trajectory":trajectory}

def reclosure_comparison(payload: dict) -> dict:
    prior=payload.get("prior",{}); current=payload.get("current",{})
    prior_health=float(prior.get("control_health_score",0) or 0); current_health=float(current.get("control_health_score",0) or 0)
    return {"control_health_delta":round(current_health-prior_health,2),"same_root_cause":bool(prior.get("root_cause_id") and prior.get("root_cause_id")==current.get("root_cause_id")),"same_control":bool(prior.get("control_id") and prior.get("control_id")==current.get("control_id")),"prior_recertification_version_id":prior.get("recovery_recertification_version_id"),"prior_reclosure_version_id":prior.get("sustainability_reclosure_version_id"),"human_interpretation_required":True}

def regulator_followup_correlation(payload: dict) -> dict:
    items=payload.get("followups",[])
    overdue=[x for x in items if bool(x.get("overdue")) or str(x.get("status","")).lower() in {"overdue","breached"}]
    recurrence=[x for x in items if bool(x.get("linked_to_recurrence"))]
    return {"followup_count":len(items),"overdue_followup_count":len(overdue),"recurrence_linked_followup_count":len(recurrence),"regulator_attention_escalation":bool(overdue or recurrence)}

def enterprise_materiality(payload: dict) -> dict:
    recurrence=int(payload.get("failed_cycle_count",0) or 0); entities=int(payload.get("affected_entity_count",0) or 0)
    decay=float(payload.get("recovery_decay_score",0) or 0); rebound=float(payload.get("peak_rebound",0) or 0)
    regulator=bool(payload.get("regulator_attention_escalation")); critical=bool(payload.get("critical_service_impact"))
    score=min(100.0, round(recurrence*18 + min(entities,5)*8 + decay*0.25 + min(rebound,50)*0.25 + (12 if regulator else 0) + (15 if critical else 0),2))
    tier=4 if score>=75 else 3 if score>=50 else 2 if score>=25 else 1
    return {"enterprise_materiality_score":score,"supervisory_escalation_tier":tier,"materiality_level":"critical" if tier==4 else "high" if tier==3 else "moderate" if tier==2 else "low","mandatory_executive_internal_audit_challenge":recurrence>=2 or tier>=3,"human_investigation_required":tier>=2}
