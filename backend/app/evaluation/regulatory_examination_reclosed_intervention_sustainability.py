from __future__ import annotations
import hashlib, json


def version_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()


def sustainability_health(payload: dict) -> dict:
    baseline=float(payload.get("baseline_control_health",100.0)); current=float(payload.get("current_control_health",baseline))
    floor=float(payload.get("minimum_control_health",80.0)); decay=max(0.0, baseline-current)
    alerts=[]
    if current < floor: alerts.append("control_health_below_threshold")
    if decay >= float(payload.get("material_decay_threshold",15.0)): alerts.append("material_control_health_decay")
    return {"baseline_control_health":round(baseline,2),"current_control_health":round(current,2),"control_health_decay":round(decay,2),"sustainability_at_risk":bool(alerts),"alerts":alerts,"human_review_required":bool(alerts)}


def multi_cycle_recurrence(payload: dict) -> dict:
    cycles=payload.get("cycles",[])
    confirmed=[c for c in cycles if c.get("confirmed_recurrence") is True]
    failed=[c for c in cycles if c.get("intervention_effective") is False]
    entities=sorted({e for c in confirmed for e in c.get("entity_ids",[])})
    examinations=sorted({str(c.get("examination_id")) for c in confirmed if c.get("examination_id")})
    recurrence_count=len(confirmed)
    repeated_failure_count=len(failed)
    score=min(100, recurrence_count*22 + repeated_failure_count*18 + min(len(entities),5)*5 + min(len(examinations),5)*4)
    tier="critical" if score>=80 else "high" if score>=60 else "moderate" if score>=35 else "low"
    repeated_systemic_failure=recurrence_count>=2 or repeated_failure_count>=2
    return {"confirmed_recurrence_count":recurrence_count,"repeated_intervention_failure_count":repeated_failure_count,"affected_entity_ids":entities,"examination_ids":examinations,"multi_cycle_recurrence_score":score,"supervisory_tier":tier,"repeated_systemic_failure":repeated_systemic_failure,"executive_review_required":repeated_systemic_failure,"internal_audit_review_required":repeated_systemic_failure,"automatic_reopening_allowed":False}


def prior_reclosure_comparison(prior: dict, current: dict) -> dict:
    prior_causes=set(prior.get("root_cause_ids",[])); current_causes=set(current.get("root_cause_ids",[]))
    prior_controls=set(prior.get("control_ids",[])); current_controls=set(current.get("control_ids",[]))
    shared_causes=sorted(prior_causes & current_causes); shared_controls=sorted(prior_controls & current_controls)
    prior_risk=float(prior.get("residual_systemic_risk_score",0)); current_risk=float(current.get("current_systemic_risk_score",0))
    return {"shared_root_cause_ids":shared_causes,"shared_control_ids":shared_controls,"systemic_risk_rebound":round(max(0.0,current_risk-prior_risk),2),"same_failure_pattern":bool(shared_causes or shared_controls),"human_validation_required":True}


def cross_entity_propagation(payload: dict) -> dict:
    observed=set(payload.get("observed_entity_ids",[])); in_scope=set(payload.get("in_scope_entity_ids",[])); impacted=sorted(observed & in_scope)
    ratio=(len(impacted)/len(in_scope)) if in_scope else 0.0
    return {"in_scope_entity_count":len(in_scope),"impacted_entity_count":len(impacted),"impacted_entity_ids":impacted,"propagation_ratio":round(ratio,4),"enterprise_propagation":len(impacted)>=2 or ratio>=0.5,"human_review_required":bool(impacted)}


def regulator_follow_up_correlation(payload: dict) -> dict:
    followups=payload.get("follow_ups",[])
    open_items=[f for f in followups if str(f.get("status","open")).lower() not in {"closed","resolved","complete"}]
    repeated=[f for f in followups if f.get("same_theme_as_reclosed_program") is True]
    return {"follow_up_count":len(followups),"open_follow_up_count":len(open_items),"same_theme_follow_up_count":len(repeated),"regulatory_follow_up_risk":bool(open_items or repeated),"documented_regulator_position_only":True}


def enterprise_materiality(payload: dict) -> dict:
    recurrence=float(payload.get("multi_cycle_recurrence_score",0)); entity_ratio=float(payload.get("propagation_ratio",0)); risk_rebound=float(payload.get("systemic_risk_rebound",0)); followup=1 if payload.get("regulatory_follow_up_risk") else 0
    score=min(100, round(recurrence*.5 + min(1,max(0,entity_ratio))*25 + min(25,max(0,risk_rebound)) + followup*10,2))
    tier="critical" if score>=80 else "high" if score>=60 else "moderate" if score>=35 else "low"
    return {"enterprise_materiality_score":score,"enterprise_materiality_tier":tier,"supervisory_escalation_required":tier in {"high","critical"},"human_decision_required":True}
