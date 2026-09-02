from __future__ import annotations
import hashlib
import json


def version_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()


def multi_cycle_enterprise_recovery_decay(payload: dict) -> dict:
    baseline = float(payload.get("release97_reclosure_control_health_score", payload.get("reclosure_control_health_score", 100)) or 100)
    current = float(payload.get("current_control_health_score", baseline) or baseline)
    regressions = int(payload.get("systemic_control_retransformation_regressions", payload.get("control_retransformation_regressions", 0)) or 0)
    repeat_cycles = int(payload.get("prior_enterprise_recovery_failure_cycles", 0) or 0)
    breaches = int(payload.get("sustainability_breach_count", 0) or 0)
    stale = int(payload.get("stale_evidence_count", 0) or 0)
    adverse_tests = int(payload.get("adverse_control_test_count", 0) or 0)
    commitment_breaches = int(payload.get("regulatory_commitment_breach_count", 0) or 0)
    health_decay = max(0.0, baseline - current)
    cycle_factor = min(repeat_cycles, 8) * 6.0
    score = min(100.0, round(
        health_decay * 0.70
        + regressions * 14
        + breaches * 10
        + stale * 2.5
        + adverse_tests * 8
        + commitment_breaches * 6
        + cycle_factor,
        2,
    ))
    level = "critical" if score >= 75 else "high" if score >= 50 else "moderate" if score >= 25 else "low"
    return {
        "multi_cycle_enterprise_recovery_decay_score": score,
        "decay_level": level,
        "control_health_delta": round(current - baseline, 2),
        "systemic_control_retransformation_regressions": regressions,
        "prior_enterprise_recovery_failure_cycles": repeat_cycles,
        "sustainability_breach_count": breaches,
        "regulatory_commitment_breach_count": commitment_breaches,
        "repeated_enterprise_recovery_failure_candidate": repeat_cycles >= 2 and (regressions > 0 or breaches > 0 or health_decay >= 10 or commitment_breaches > 0),
        "human_investigation_required": score >= 25 or regressions > 0 or adverse_tests > 0 or commitment_breaches > 0,
        "automatic_investigation_opening_allowed": False,
        "automatic_reopening_allowed": False,
    }


def systemic_control_retransformation_regression(payload: dict) -> dict:
    controls = payload.get("controls", [])
    regressed, severe, repeated, missing = [], [], [], []
    for control in controls:
        cid = str(control.get("control_id", ""))
        prior = str(control.get("release97_reclosure_status", control.get("prior_status", ""))).lower()
        current = str(control.get("current_status", control.get("status", ""))).lower()
        failure_count = int(control.get("post_reclosure_failure_count", control.get("failure_count", 0)) or 0)
        regressed_flag = bool(control.get("regression")) or current in {"degraded", "failed", "ineffective", "recurred"} or (prior in {"effective", "stable", "passed"} and current not in {"effective", "stable", "passed"})
        if regressed_flag:
            regressed.append(cid)
            if str(control.get("severity", "")).lower() in {"high", "critical"} or failure_count >= 2:
                severe.append(cid)
            if failure_count >= 2 or bool(control.get("repeated_failure")):
                repeated.append(cid)
            if not control.get("evidence_refs"):
                missing.append(cid)
    denominator = max(1, len(controls))
    pct = round(100.0 * len(set(regressed)) / denominator, 2)
    threshold = float(payload.get("material_regression_threshold_percent", 20) or 20)
    return {
        "control_count": len(controls),
        "regressed_control_ids": sorted(x for x in set(regressed) if x),
        "severe_regressed_control_ids": sorted(x for x in set(severe) if x),
        "repeated_failure_regressed_control_ids": sorted(x for x in set(repeated) if x),
        "missing_evidence_control_ids": sorted(x for x in set(missing) if x),
        "systemic_control_retransformation_regression_percent": pct,
        "material_systemic_control_regression_candidate": bool(severe) or bool(repeated) or pct >= threshold,
        "human_validation_required": bool(regressed),
    }


def systemic_risk_rebound(payload: dict) -> dict:
    baseline = float(payload.get("release97_reclosure_systemic_risk_score", payload.get("reclosure_systemic_risk_score", 0)) or 0)
    current = float(payload.get("current_systemic_risk_score", baseline) or baseline)
    peak = float(payload.get("peak_post_reclosure_systemic_risk_score", current) or current)
    rebound = max(0.0, current - baseline)
    pct = round(rebound / baseline * 100, 2) if baseline > 0 else (100.0 if rebound > 0 else 0.0)
    threshold = float(payload.get("rebound_threshold_percent", 20) or 20)
    absolute = float(payload.get("absolute_rebound_threshold", 15) or 15)
    return {
        "release97_reclosure_systemic_risk_score": baseline,
        "current_systemic_risk_score": current,
        "systemic_risk_rebound_percent": pct,
        "peak_post_reclosure_systemic_risk_score": peak,
        "material_systemic_risk_rebound_candidate": pct >= threshold or max(0.0, peak - baseline) >= absolute,
        "human_validation_required": True,
    }


def cross_entity_recurrence(payload: dict) -> dict:
    entities = payload.get("entities", [])
    recurrent, severe, repeated, missing = [], [], [], []
    for entity in entities:
        eid = str(entity.get("entity_id", ""))
        failures = int(entity.get("post_reclosure_failure_count", entity.get("failure_count", 0)) or 0)
        recurrence = bool(entity.get("recurrence")) or failures > 0 or str(entity.get("status", "")).lower() in {"degraded", "failed", "recurred"}
        if recurrence:
            recurrent.append(eid)
        if recurrence and (failures >= 2 or str(entity.get("severity", "")).lower() in {"high", "critical"}):
            severe.append(eid)
        if recurrence and failures >= 2:
            repeated.append(eid)
        if recurrence and not entity.get("evidence_refs"):
            missing.append(eid)
    expected = max(1, int(payload.get("expected_entity_count", len(entities) or 1) or 1))
    spread = round(100.0 * len(set(recurrent)) / expected, 2)
    threshold = float(payload.get("propagation_threshold_percent", 35) or 35)
    return {
        "entity_count": len(entities),
        "recurrent_entity_ids": sorted(x for x in set(recurrent) if x),
        "severe_recurrent_entity_ids": sorted(x for x in set(severe) if x),
        "repeated_recurrent_entity_ids": sorted(x for x in set(repeated) if x),
        "missing_evidence_entity_ids": sorted(x for x in set(missing) if x),
        "cross_entity_recurrence_percent": spread,
        "cross_entity_recurrence_propagation": len(set(recurrent)) >= 2 or spread >= threshold,
        "human_investigation_required": bool(recurrent),
    }


def prior_enterprise_reclosure_comparison(payload: dict) -> dict:
    prior = payload.get("prior", {})
    current = payload.get("current", {})
    prior_health = float(prior.get("control_health_score", 0) or 0)
    current_health = float(current.get("control_health_score", 0) or 0)
    prior_risk = float(prior.get("systemic_risk_score", 0) or 0)
    current_risk = float(current.get("systemic_risk_score", 0) or 0)
    repeated_controls = sorted(set(map(str, prior.get("control_ids", []))) & set(map(str, current.get("control_ids", []))))
    repeated_roots = sorted(set(map(str, prior.get("root_cause_ids", []))) & set(map(str, current.get("root_cause_ids", []))))
    repeated_entities = sorted(set(map(str, prior.get("entity_ids", []))) & set(map(str, current.get("entity_ids", []))))
    return {
        "release97_enterprise_recovery_recertification_version_id": prior.get("enterprise_recovery_recertification_version_id"),
        "release97_enterprise_sustainability_reclosure_version_id": prior.get("enterprise_sustainability_reclosure_version_id"),
        "control_health_delta": round(current_health - prior_health, 2),
        "systemic_risk_delta": round(current_risk - prior_risk, 2),
        "repeated_control_ids": repeated_controls,
        "repeated_root_cause_ids": repeated_roots,
        "repeated_entity_ids": repeated_entities,
        "prior_enterprise_reclosure_degradation_candidate": current_health < prior_health or current_risk > prior_risk or bool(repeated_controls or repeated_roots or repeated_entities),
        "human_interpretation_required": True,
    }


def examination_finding_correlation(payload: dict) -> dict:
    items = payload.get("items", [])
    matches = []
    for item in items:
        score = round((
            float(item.get("root_cause_similarity", 0) or 0) * .35
            + float(item.get("control_overlap", 0) or 0) * .30
            + float(item.get("entity_overlap", 0) or 0) * .15
            + float(item.get("regulatory_obligation_overlap", 0) or 0) * .20
        ) * 100, 2)
        if score >= float(item.get("match_threshold", 70) or 70):
            matches.append({"examination_id": item.get("examination_id"), "finding_id": item.get("finding_id"), "match_score": score})
    return {
        "evaluated_item_count": len(items),
        "matched_items": matches,
        "matched_item_count": len(matches),
        "new_examination_finding_correlation": bool(matches),
        "human_validation_required": True,
        "regulator_intent_inferred": False,
    }


def regulator_followup_linkage(payload: dict) -> dict:
    items = payload.get("followups", [])
    linked = [item for item in items if bool(item.get("linked_to_enterprise_decay")) or bool(item.get("linked_to_recurrence")) or bool(item.get("linked_to_reclosed_enterprise_recovery"))]
    adverse = [item for item in linked if bool(item.get("adverse")) or bool(item.get("overdue")) or str(item.get("status", "")).lower() in {"overdue", "breached", "adverse"}]
    return {
        "followup_count": len(items),
        "linked_followup_count": len(linked),
        "adverse_linked_followup_count": len(adverse),
        "regulator_followup_escalation_candidate": bool(adverse),
        "human_interpretation_required": True,
        "regulator_intent_inferred": False,
    }


def enterprise_materiality(payload: dict) -> dict:
    decay = float(payload.get("multi_cycle_enterprise_recovery_decay_score", 0) or 0)
    regression = float(payload.get("systemic_control_retransformation_regression_percent", 0) or 0)
    recurrence = float(payload.get("cross_entity_recurrence_percent", 0) or 0)
    rebound = float(payload.get("systemic_risk_rebound_percent", 0) or 0)
    repeat_cycles = int(payload.get("prior_enterprise_recovery_failure_cycles", 0) or 0)
    adverse_followups = int(payload.get("adverse_regulator_followup_count", 0) or 0)
    commitment_breaches = int(payload.get("regulatory_commitment_breach_count", 0) or 0)
    score = min(100.0, round(
        decay * .28
        + regression * .20
        + recurrence * .18
        + min(rebound, 100) * .14
        + min(repeat_cycles, 5) * 5
        + min(adverse_followups, 5) * 2
        + min(commitment_breaches, 5) * 2,
        2,
    ))
    tier = "enterprise_critical" if score >= 75 else "enterprise_high" if score >= 50 else "elevated" if score >= 25 else "routine"
    return {
        "enterprise_materiality_score": score,
        "enterprise_materiality_tier": tier,
        "executive_internal_audit_escalation_required": score >= 50 or repeat_cycles >= 3 or commitment_breaches > 0,
        "enterprise_reopening_candidate": score >= 25,
        "human_materiality_determination_required": True,
    }


def enterprise_reopening_readiness(payload: dict) -> dict:
    checks = {
        "release97_enterprise_sustainability_reclosure_reference_validated": bool(payload.get("release97_enterprise_sustainability_reclosure_reference_validated")),
        "material_systemic_recovery_decay_confirmed": bool(payload.get("material_systemic_recovery_decay_confirmed")),
        "human_investigation_complete": bool(payload.get("human_investigation_complete")),
        "independent_reassessment_complete": bool(payload.get("independent_reassessment_complete")),
        "prior_executive_recertification_reclosure_compared": bool(payload.get("prior_executive_recertification_reclosure_compared")),
        "cross_entity_recurrence_scope_validated": bool(payload.get("cross_entity_recurrence_scope_validated")),
        "new_examination_finding_links_human_validated": bool(payload.get("new_examination_finding_links_human_validated")),
        "regulator_followups_human_interpreted": bool(payload.get("regulator_followups_human_interpreted")),
        "enterprise_materiality_human_validated": bool(payload.get("enterprise_materiality_human_validated")),
        "executive_review_complete": bool(payload.get("executive_review_complete")),
        "internal_audit_challenge_complete": bool(payload.get("internal_audit_challenge_complete")),
        "renewed_enterprise_recovery_governance_candidate_prepared": bool(payload.get("renewed_enterprise_recovery_governance_candidate_prepared")),
    }
    blockers = [key for key, value in checks.items() if not value]
    score = round(sum(checks.values()) / len(checks) * 100, 2)
    return {
        "gates": checks,
        "blockers": blockers,
        "enterprise_reopening_readiness_score": score,
        "ready_for_human_enterprise_reopening": not blockers,
        "human_reopening_required": True,
        "automatic_reopening_allowed": False,
    }


def supervisory_dashboard_summary(payload: dict) -> dict:
    decay = multi_cycle_enterprise_recovery_decay(payload)
    regression = systemic_control_retransformation_regression(payload)
    rebound = systemic_risk_rebound(payload)
    recurrence = cross_entity_recurrence(payload)
    followups = regulator_followup_linkage(payload)
    materiality = enterprise_materiality({
        **payload,
        **decay,
        **regression,
        **rebound,
        **recurrence,
        "adverse_regulator_followup_count": followups["adverse_linked_followup_count"],
    })
    return {
        "recovery_program_id": payload.get("recovery_program_id"),
        "decay": decay,
        "control_regression": regression,
        "risk_rebound": rebound,
        "cross_entity_recurrence": recurrence,
        "materiality": materiality,
        "human_decision_required": True,
    }


def audit_export_manifest(payload: dict) -> dict:
    refs = sorted(set(str(x) for x in payload.get("evidence_refs", []) if x))
    return {
        "tenant_id": payload.get("tenant_id"),
        "recovery_program_id": payload.get("recovery_program_id"),
        "release97_enterprise_sustainability_reclosure_version_id": payload.get("release97_enterprise_sustainability_reclosure_version_id"),
        "evidence_refs": refs,
        "evidence_count": len(refs),
        "manifest_hash": version_hash({
            "tenant_id": payload.get("tenant_id"),
            "recovery_program_id": payload.get("recovery_program_id"),
            "release97_enterprise_sustainability_reclosure_version_id": payload.get("release97_enterprise_sustainability_reclosure_version_id"),
            "evidence_refs": refs,
        }),
        "immutable": True,
    }
