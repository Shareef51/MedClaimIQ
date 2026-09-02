from __future__ import annotations
import hashlib, json

def version_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()

def repeated_recovery_decay(payload: dict) -> dict:
    baseline=float(payload.get("reclosure_control_health_score",100) or 100)
    current=float(payload.get("current_control_health_score",baseline) or baseline)
    repeated_failures=int(payload.get("repeated_failure_control_regressions",0) or 0)
    breaches=int(payload.get("sustainability_breach_count",0) or 0)
    stale=int(payload.get("stale_evidence_count",0) or 0)
    days=int(payload.get("days_since_reclosure",0) or 0)
    previous_cycles=int(payload.get("prior_recovery_failure_cycles",0) or 0)
    health_decay=max(0.0,baseline-current)
    score=min(100.0,round(health_decay*0.8 + repeated_failures*14 + breaches*12 + stale*4 + min(days/30,12)*1.25 + min(previous_cycles,5)*5,2))
    level="critical" if score>=75 else "high" if score>=50 else "moderate" if score>=25 else "low"
    return {
        "repeated_recovery_decay_score":score,
        "decay_level":level,
        "control_health_delta":round(current-baseline,2),
        "repeated_failure_control_regressions":repeated_failures,
        "sustainability_breach_count":breaches,
        "human_investigation_required":score>=25 or repeated_failures>0,
        "automatic_reopening_allowed":False,
    }

def systemic_risk_rebound(payload: dict) -> dict:
    baseline=float(payload.get("reclosure_systemic_risk_score",0) or 0)
    current=float(payload.get("current_systemic_risk_score",baseline) or baseline)
    peak=float(payload.get("peak_post_reclosure_risk_score",current) or current)
    rebound=max(0.0,current-baseline)
    peak_rebound=max(0.0,peak-baseline)
    pct=round(rebound/baseline*100,2) if baseline>0 else (100.0 if rebound>0 else 0.0)
    threshold=float(payload.get("rebound_threshold_percent",20) or 20)
    return {
        "reclosure_systemic_risk_score":baseline,
        "current_systemic_risk_score":current,
        "systemic_risk_rebound":rebound>0,
        "systemic_risk_rebound_percent":pct,
        "peak_rebound":round(peak_rebound,2),
        "rebound_threshold_percent":threshold,
        "material_rebound_candidate":pct>=threshold or peak_rebound>=float(payload.get("absolute_rebound_threshold",15) or 15),
        "human_validation_required":True,
    }

def cross_entity_recurrence(payload: dict) -> dict:
    entities=payload.get("entities",[])
    recurrent=[]; severe=[]; missing=[]
    for e in entities:
        eid=str(e.get("entity_id",""))
        recurrence=bool(e.get("recurrence")) or int(e.get("failure_count",0) or 0)>=1 or str(e.get("status","" )).lower() in {"degraded","failed","recurred"}
        if recurrence: recurrent.append(eid)
        if recurrence and (str(e.get("severity","" )).lower() in {"high","critical"} or int(e.get("failure_count",0) or 0)>=2): severe.append(eid)
        if recurrence and not e.get("evidence_refs"): missing.append(eid)
    expected=max(1,int(payload.get("expected_entity_count",len(entities) or 1) or 1))
    spread=round(100.0*len(set(recurrent))/expected,2)
    return {
        "entity_count":len(entities),
        "recurrent_entity_ids":sorted(x for x in set(recurrent) if x),
        "severe_recurrent_entity_ids":sorted(x for x in set(severe) if x),
        "missing_evidence_entity_ids":sorted(x for x in set(missing) if x),
        "recurrence_propagation_percent":spread,
        "cross_entity_recurrence_propagation":len(set(recurrent))>=2 or spread>=float(payload.get("propagation_threshold_percent",40) or 40),
        "human_investigation_required":bool(recurrent),
    }

def prior_reclosure_comparison(payload: dict) -> dict:
    prior=payload.get("prior",{}); current=payload.get("current",{})
    prior_health=float(prior.get("control_health_score",0) or 0); current_health=float(current.get("control_health_score",0) or 0)
    prior_risk=float(prior.get("systemic_risk_score",0) or 0); current_risk=float(current.get("systemic_risk_score",0) or 0)
    same_controls=sorted(set(map(str,prior.get("control_ids",[]))) & set(map(str,current.get("control_ids",[]))))
    same_roots=sorted(set(map(str,prior.get("root_cause_ids",[]))) & set(map(str,current.get("root_cause_ids",[]))))
    return {
        "prior_recovery_recertification_version_id":prior.get("recovery_recertification_version_id"),
        "prior_sustainability_reclosure_version_id":prior.get("sustainability_reclosure_version_id"),
        "control_health_delta":round(current_health-prior_health,2),
        "systemic_risk_delta":round(current_risk-prior_risk,2),
        "repeated_control_ids":same_controls,
        "repeated_root_cause_ids":same_roots,
        "prior_reclosure_degradation_candidate":current_health<prior_health or current_risk>prior_risk or bool(same_controls or same_roots),
        "human_interpretation_required":True,
    }

def examination_finding_correlation(payload: dict) -> dict:
    items=payload.get("items",[]); matches=[]
    for x in items:
        root=float(x.get("root_cause_similarity",0) or 0); control=float(x.get("control_overlap",0) or 0); entity=float(x.get("entity_overlap",0) or 0); obligation=float(x.get("regulatory_obligation_overlap",0) or 0)
        score=round((root*.35+control*.30+entity*.15+obligation*.20)*100,2)
        if score>=float(x.get("match_threshold",70) or 70):
            matches.append({"examination_id":x.get("examination_id"),"finding_id":x.get("finding_id"),"match_score":score})
    return {"evaluated_item_count":len(items),"matched_items":matches,"matched_item_count":len(matches),"new_examination_finding_correlation":bool(matches),"human_validation_required":True,"regulator_intent_inferred":False}

def regulator_followup_linkage(payload: dict) -> dict:
    items=payload.get("followups",[])
    linked=[x for x in items if bool(x.get("linked_to_recovery_decay")) or bool(x.get("linked_to_recurrence"))]
    adverse=[x for x in linked if bool(x.get("adverse")) or bool(x.get("overdue")) or str(x.get("status","" )).lower() in {"overdue","breached","adverse"}]
    return {"followup_count":len(items),"linked_followup_count":len(linked),"adverse_linked_followup_count":len(adverse),"regulator_followup_escalation_candidate":bool(adverse),"regulator_intent_inferred":False,"human_interpretation_required":True}

def enterprise_reopening_readiness(payload: dict) -> dict:
    checks={
        "material_decay_confirmed":bool(payload.get("material_decay_confirmed")),
        "human_investigation_complete":bool(payload.get("human_investigation_complete")),
        "independent_reassessment_complete":bool(payload.get("independent_reassessment_complete")),
        "prior_recertification_reclosure_compared":bool(payload.get("prior_recertification_reclosure_compared")),
        "cross_entity_scope_validated":bool(payload.get("cross_entity_scope_validated")),
        "new_examination_finding_links_human_validated":bool(payload.get("new_examination_finding_links_human_validated")),
        "regulator_followups_human_interpreted":bool(payload.get("regulator_followups_human_interpreted")),
        "executive_review_complete":bool(payload.get("executive_review_complete")),
        "internal_audit_challenge_complete":bool(payload.get("internal_audit_challenge_complete")),
        "renewed_recovery_governance_candidate_prepared":bool(payload.get("renewed_recovery_governance_candidate_prepared")),
    }
    blockers=[k for k,v in checks.items() if not v]
    score=round(100.0*sum(checks.values())/len(checks),2)
    return {"enterprise_reopening_readiness_score":score,"checks":checks,"blocking_items":blockers,"ready_for_human_enterprise_reopening":not blockers,"automated_reopening_allowed":False}
