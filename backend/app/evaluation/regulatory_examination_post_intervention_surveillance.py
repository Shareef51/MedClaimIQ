from __future__ import annotations
import hashlib, json


def version_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()


def systemic_recurrence_signal(payload: dict) -> dict:
    baseline=float(payload.get("closure_systemic_risk_score",0) or 0)
    current=float(payload.get("current_systemic_risk_score",0) or 0)
    rebound=max(0.0,current-baseline)
    decay=float(payload.get("control_effectiveness_decay_percent",0) or 0)
    recurrence_count=int(payload.get("new_recurrence_count",0) or 0)
    regulator_followup=bool(payload.get("regulator_followup_reopened",False))
    threshold=float(payload.get("systemic_risk_rebound_threshold",15) or 15)
    trigger=rebound>=threshold or decay>=float(payload.get("control_decay_threshold_percent",20) or 20) or recurrence_count>0 or regulator_followup
    reasons=[]
    if rebound>=threshold: reasons.append("systemic_risk_rebound")
    if decay>=float(payload.get("control_decay_threshold_percent",20) or 20): reasons.append("control_effectiveness_decay")
    if recurrence_count>0: reasons.append("new_recurrence_detected")
    if regulator_followup: reasons.append("regulator_followup_reopened")
    return {"systemic_risk_rebound":round(rebound,2),"reopen_candidate":trigger,"reasons":reasons,"human_reopening_required":trigger,"automated_reopening_allowed":False}


def examination_match(payload: dict) -> dict:
    obligation_overlap=float(payload.get("obligation_overlap",0) or 0)
    control_overlap=float(payload.get("control_overlap",0) or 0)
    root_cause_similarity=float(payload.get("root_cause_similarity",0) or 0)
    entity_overlap=float(payload.get("entity_overlap",0) or 0)
    score=round((obligation_overlap*.30)+(control_overlap*.30)+(root_cause_similarity*.25)+(entity_overlap*.15),4)
    threshold=float(payload.get("match_threshold",0.65) or .65)
    return {"match_score":score,"likely_related":score>=threshold,"human_validation_required":score>=threshold,"authoritative_regulatory_conclusion":False}


def cross_entity_propagation(payload: dict) -> dict:
    affected=set(payload.get("affected_entity_ids",[]))
    required=set(payload.get("program_entity_ids",[]))
    ratio=0.0 if not required else len(affected & required)/len(required)
    systemic=bool(len(affected)>=2 or ratio>=float(payload.get("systemic_entity_ratio_threshold",0.5) or .5))
    return {"affected_entity_count":len(affected),"program_entity_coverage":round(ratio,4),"cross_entity_systemic_candidate":systemic,"human_review_required":systemic}


def reopening_readiness(payload: dict) -> dict:
    blockers=[]
    if payload.get("investigation_complete") is not True: blockers.append("recurrence_investigation_incomplete")
    if payload.get("independent_reassessment_complete") is not True: blockers.append("independent_reassessment_incomplete")
    if payload.get("executive_review_complete") is not True: blockers.append("executive_review_incomplete")
    if payload.get("internal_audit_review_complete") is not True: blockers.append("internal_audit_review_incomplete")
    if payload.get("renewed_remediation_candidate_defined") is not True: blockers.append("renewed_remediation_candidate_missing")
    score=max(0,100-(20*len(blockers)))
    return {"reopening_readiness_score":score,"blockers":blockers,"ready_for_human_reopening_decision":not blockers,"human_reopening_required":True,"automated_reopening_allowed":False}
