from __future__ import annotations
import hashlib
import json


def version_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()


def multi_cycle_supervisory_recovery_decay(payload: dict) -> dict:
    baseline = float(payload.get("release93_reclosure_control_health_score", payload.get("reclosure_control_health_score", 100)) or 100)
    current = float(payload.get("current_control_health_score", baseline) or baseline)
    regressions = int(payload.get("control_retransformation_regressions", 0) or 0)
    repeat_cycles = int(payload.get("prior_supervisory_recovery_failure_cycles", 0) or 0)
    breaches = int(payload.get("sustainability_breach_count", 0) or 0)
    stale = int(payload.get("stale_evidence_count", 0) or 0)
    adverse_tests = int(payload.get("adverse_control_test_count", 0) or 0)
    health_decay = max(0.0, baseline-current)
    cycle_factor = min(repeat_cycles, 6) * 6.0
    score = min(100.0, round(health_decay*0.75 + regressions*15 + breaches*11 + stale*3 + adverse_tests*8 + cycle_factor, 2))
    level = "critical" if score >= 75 else "high" if score >= 50 else "moderate" if score >= 25 else "low"
    return {
        "multi_cycle_supervisory_recovery_decay_score": score,
        "decay_level": level,
        "control_health_delta": round(current-baseline, 2),
        "control_retransformation_regressions": regressions,
        "prior_supervisory_recovery_failure_cycles": repeat_cycles,
        "sustainability_breach_count": breaches,
        "repeated_supervisory_recovery_failure_candidate": repeat_cycles >= 2 and (regressions > 0 or breaches > 0 or health_decay >= 10),
        "human_investigation_required": score >= 25 or regressions > 0 or adverse_tests > 0,
        "automatic_investigation_opening_allowed": False,
        "automatic_reopening_allowed": False,
    }


def control_retransformation_regression(payload: dict) -> dict:
    controls = payload.get("controls", [])
    regressed, severe, missing = [], [], []
    for c in controls:
        cid = str(c.get("control_id", ""))
        prior = str(c.get("release93_reclosure_status", c.get("prior_status", ""))).lower()
        current = str(c.get("current_status", c.get("status", ""))).lower()
        failure_count = int(c.get("post_reclosure_failure_count", c.get("failure_count", 0)) or 0)
        is_regressed = bool(c.get("regression")) or current in {"degraded", "failed", "ineffective", "recurred"} or (prior in {"effective", "stable", "passed"} and current not in {"effective", "stable", "passed"})
        if is_regressed:
            regressed.append(cid)
            if str(c.get("severity", "")).lower() in {"high", "critical"} or failure_count >= 2:
                severe.append(cid)
            if not c.get("evidence_refs"):
                missing.append(cid)
    total=max(1, len(controls))
    pct=round(100.0*len(set(regressed))/total, 2)
    return {
        "control_count": len(controls),
        "regressed_control_ids": sorted(x for x in set(regressed) if x),
        "severe_regressed_control_ids": sorted(x for x in set(severe) if x),
        "missing_evidence_control_ids": sorted(x for x in set(missing) if x),
        "control_retransformation_regression_percent": pct,
        "material_control_regression_candidate": bool(severe) or pct >= float(payload.get("material_regression_threshold_percent", 25) or 25),
        "human_validation_required": bool(regressed),
    }


def systemic_risk_rebound(payload: dict) -> dict:
    baseline = float(payload.get("release93_reclosure_systemic_risk_score", payload.get("reclosure_systemic_risk_score", 0)) or 0)
    current = float(payload.get("current_systemic_risk_score", baseline) or baseline)
    peak = float(payload.get("peak_post_reclosure_systemic_risk_score", current) or current)
    rebound=max(0.0, current-baseline)
    pct=round(rebound/baseline*100, 2) if baseline > 0 else (100.0 if rebound > 0 else 0.0)
    threshold=float(payload.get("rebound_threshold_percent", 20) or 20)
    return {
        "release93_reclosure_systemic_risk_score": baseline,
        "current_systemic_risk_score": current,
        "systemic_risk_rebound_percent": pct,
        "peak_post_reclosure_systemic_risk_score": peak,
        "material_systemic_risk_rebound_candidate": pct >= threshold or max(0.0, peak-baseline) >= float(payload.get("absolute_rebound_threshold", 15) or 15),
        "human_validation_required": True,
    }


def cross_entity_recurrence(payload: dict) -> dict:
    entities=payload.get("entities", [])
    recurrent=[]; severe=[]; missing=[]
    for e in entities:
        eid=str(e.get("entity_id", ""))
        failures=int(e.get("post_reclosure_failure_count", e.get("failure_count", 0)) or 0)
        recurrence=bool(e.get("recurrence")) or failures > 0 or str(e.get("status", "")).lower() in {"degraded", "failed", "recurred"}
        if recurrence: recurrent.append(eid)
        if recurrence and (failures >= 2 or str(e.get("severity", "")).lower() in {"high", "critical"}): severe.append(eid)
        if recurrence and not e.get("evidence_refs"): missing.append(eid)
    expected=max(1, int(payload.get("expected_entity_count", len(entities) or 1) or 1))
    spread=round(100.0*len(set(recurrent))/expected, 2)
    threshold=float(payload.get("propagation_threshold_percent", 40) or 40)
    return {
        "entity_count": len(entities),
        "recurrent_entity_ids": sorted(x for x in set(recurrent) if x),
        "severe_recurrent_entity_ids": sorted(x for x in set(severe) if x),
        "missing_evidence_entity_ids": sorted(x for x in set(missing) if x),
        "cross_entity_recurrence_percent": spread,
        "cross_entity_recurrence_propagation": len(set(recurrent)) >= 2 or spread >= threshold,
        "human_investigation_required": bool(recurrent),
    }


def prior_supervisory_reclosure_comparison(payload: dict) -> dict:
    prior=payload.get("prior", {}); current=payload.get("current", {})
    prior_health=float(prior.get("control_health_score", 0) or 0); current_health=float(current.get("control_health_score", 0) or 0)
    prior_risk=float(prior.get("systemic_risk_score", 0) or 0); current_risk=float(current.get("systemic_risk_score", 0) or 0)
    repeated_controls=sorted(set(map(str, prior.get("control_ids", []))) & set(map(str, current.get("control_ids", []))))
    repeated_roots=sorted(set(map(str, prior.get("root_cause_ids", []))) & set(map(str, current.get("root_cause_ids", []))))
    repeated_entities=sorted(set(map(str, prior.get("entity_ids", []))) & set(map(str, current.get("entity_ids", []))))
    return {
        "release93_supervisory_recovery_recertification_version_id": prior.get("supervisory_recovery_recertification_version_id"),
        "release93_supervisory_sustainability_reclosure_version_id": prior.get("supervisory_sustainability_reclosure_version_id"),
        "control_health_delta": round(current_health-prior_health, 2),
        "systemic_risk_delta": round(current_risk-prior_risk, 2),
        "repeated_control_ids": repeated_controls,
        "repeated_root_cause_ids": repeated_roots,
        "repeated_entity_ids": repeated_entities,
        "prior_supervisory_reclosure_degradation_candidate": current_health < prior_health or current_risk > prior_risk or bool(repeated_controls or repeated_roots),
        "human_interpretation_required": True,
    }


def examination_finding_correlation(payload: dict) -> dict:
    items=payload.get("items", []); matches=[]
    for x in items:
        score=round((float(x.get("root_cause_similarity",0) or 0)*.35 + float(x.get("control_overlap",0) or 0)*.30 + float(x.get("entity_overlap",0) or 0)*.15 + float(x.get("regulatory_obligation_overlap",0) or 0)*.20)*100, 2)
        if score >= float(x.get("match_threshold", 70) or 70):
            matches.append({"examination_id":x.get("examination_id"), "finding_id":x.get("finding_id"), "match_score":score})
    return {"evaluated_item_count":len(items), "matched_items":matches, "matched_item_count":len(matches), "new_examination_finding_correlation":bool(matches), "human_validation_required":True, "regulator_intent_inferred":False}


def regulator_followup_linkage(payload: dict) -> dict:
    items=payload.get("followups", [])
    linked=[x for x in items if bool(x.get("linked_to_supervisory_decay")) or bool(x.get("linked_to_recurrence")) or bool(x.get("linked_to_reclosed_recovery"))]
    adverse=[x for x in linked if bool(x.get("adverse")) or bool(x.get("overdue")) or str(x.get("status", "")).lower() in {"overdue", "breached", "adverse"}]
    return {"followup_count":len(items), "linked_followup_count":len(linked), "adverse_linked_followup_count":len(adverse), "regulator_followup_escalation_candidate":bool(adverse), "human_interpretation_required":True, "regulator_intent_inferred":False}


def enterprise_materiality(payload: dict) -> dict:
    decay=float(payload.get("multi_cycle_supervisory_recovery_decay_score", 0) or 0)
    regression=float(payload.get("control_retransformation_regression_percent", 0) or 0)
    recurrence=float(payload.get("cross_entity_recurrence_percent", 0) or 0)
    rebound=float(payload.get("systemic_risk_rebound_percent", 0) or 0)
    repeat_cycles=int(payload.get("prior_supervisory_recovery_failure_cycles", 0) or 0)
    adverse_followups=int(payload.get("adverse_regulator_followup_count", 0) or 0)
    score=min(100.0, round(decay*.30 + regression*.20 + recurrence*.20 + min(rebound,100)*.15 + min(repeat_cycles,5)*5 + min(adverse_followups,5)*2, 2))
    tier="enterprise_critical" if score >= 75 else "enterprise_high" if score >= 50 else "elevated" if score >= 25 else "routine"
    return {
        "enterprise_materiality_score": score,
        "enterprise_materiality_tier": tier,
        "executive_internal_audit_escalation_required": score >= 50 or repeat_cycles >= 3,
        "renewed_reopening_candidate": score >= 25,
        "human_materiality_determination_required": True,
    }


def enterprise_reopening_readiness(payload: dict) -> dict:
    checks={
        "release93_supervisory_reclosure_reference_validated": bool(payload.get("release93_supervisory_reclosure_reference_validated")),
        "material_multi_cycle_decay_confirmed": bool(payload.get("material_multi_cycle_decay_confirmed")),
        "human_investigation_complete": bool(payload.get("human_investigation_complete")),
        "independent_reassessment_complete": bool(payload.get("independent_reassessment_complete")),
        "prior_executive_recertification_reclosure_compared": bool(payload.get("prior_executive_recertification_reclosure_compared")),
        "cross_entity_recurrence_scope_validated": bool(payload.get("cross_entity_recurrence_scope_validated")),
        "new_examination_finding_links_human_validated": bool(payload.get("new_examination_finding_links_human_validated")),
        "regulator_followups_human_interpreted": bool(payload.get("regulator_followups_human_interpreted")),
        "enterprise_materiality_human_validated": bool(payload.get("enterprise_materiality_human_validated")),
        "executive_review_complete": bool(payload.get("executive_review_complete")),
        "internal_audit_challenge_complete": bool(payload.get("internal_audit_challenge_complete")),
        "renewed_recovery_governance_candidate_prepared": bool(payload.get("renewed_recovery_governance_candidate_prepared")),
    }
    blockers=[k for k,v in checks.items() if not v]
    score=round(sum(checks.values())/len(checks)*100, 2)
    return {"gates":checks, "blockers":blockers, "enterprise_reopening_readiness_score":score, "ready_for_human_enterprise_reopening":not blockers, "human_reopening_required":True, "automatic_reopening_allowed":False}
