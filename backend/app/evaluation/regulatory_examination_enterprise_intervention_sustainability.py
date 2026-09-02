from __future__ import annotations
import hashlib, json


def version_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()


def systemic_risk_reduction(payload: dict) -> dict:
    baseline=float(payload.get("baseline_systemic_risk_score",100))
    current=float(payload.get("post_remediation_systemic_risk_score",100))
    reduction=max(0.0,baseline-current)
    pct=0.0 if baseline<=0 else round((reduction/baseline)*100,2)
    target=float(payload.get("minimum_reduction_percent",50))
    return {"baseline_systemic_risk_score":baseline,"post_remediation_systemic_risk_score":current,"absolute_risk_reduction":round(reduction,2),"risk_reduction_percent":pct,"target_met":pct>=target,"recommendation_only":True}


def sustainability_assurance(payload: dict) -> dict:
    observations=payload.get("sustainability_observations",[])
    required=set(payload.get("required_entity_ids",[]))
    observed=set(x.get("entity_id") for x in observations if x.get("entity_id"))
    healthy=[x for x in observations if x.get("control_effective") is True and x.get("recurrence_detected") is not True]
    failed=[x for x in observations if x.get("control_effective") is False or x.get("recurrence_detected") is True]
    coverage=1.0 if not required else len(required & observed)/len(required)
    healthy_ratio=1.0 if not observations else len(healthy)/len(observations)
    window_complete=bool(payload.get("sustainability_window_complete",False))
    return {"cross_entity_coverage":round(coverage,4),"healthy_observation_ratio":round(healthy_ratio,4),"failed_or_recurrent_count":len(failed),"sustainability_window_complete":window_complete,"eligible_for_human_closure_review":bool(observations) and coverage==1.0 and not failed and window_complete,"automated_closure_allowed":False}


def intervention_closure_readiness(payload: dict) -> dict:
    blockers=[]
    if payload.get("implementation_complete") is not True: blockers.append("implementation_incomplete")
    if payload.get("independent_effectiveness_passed") is not True: blockers.append("independent_effectiveness_not_passed")
    if payload.get("sustainability_assurance_passed") is not True: blockers.append("sustainability_assurance_not_passed")
    if payload.get("cross_entity_reconciled") is not True: blockers.append("cross_entity_reconciliation_incomplete")
    if payload.get("regulatory_commitments_reconciled") is not True: blockers.append("regulatory_commitments_unreconciled")
    if int(payload.get("unresolved_blocker_count",0) or 0)>0: blockers.append("unresolved_remediation_blockers")
    if payload.get("residual_risk_accepted_by_human") is not True: blockers.append("human_residual_risk_acceptance_missing")
    weights={"implementation_complete":20,"independent_effectiveness_passed":20,"sustainability_assurance_passed":20,"cross_entity_reconciled":15,"regulatory_commitments_reconciled":10,"residual_risk_accepted_by_human":15}
    score=sum(w for k,w in weights.items() if payload.get(k) is True)
    if int(payload.get("unresolved_blocker_count",0) or 0)>0: score=max(0,score-20)
    return {"closure_readiness_score":score,"blockers":blockers,"ready_for_human_executive_closure":score==100 and not blockers,"human_closure_required":True}


def recurrence_reopen_signal(payload: dict) -> dict:
    recurrence=bool(payload.get("recurrence_detected",False))
    decay=float(payload.get("control_health_decay_percent",0) or 0)
    threshold=float(payload.get("control_health_decay_threshold_percent",20) or 20)
    regulator_followup=bool(payload.get("regulator_followup_reopened",False))
    trigger=recurrence or decay>=threshold or regulator_followup
    reasons=[]
    if recurrence: reasons.append("recurrence_detected")
    if decay>=threshold: reasons.append("control_health_decay")
    if regulator_followup: reasons.append("regulator_followup_reopened")
    return {"reopen_candidate":trigger,"reasons":reasons,"human_reopen_decision_required":trigger,"automated_reopen_allowed":False}
