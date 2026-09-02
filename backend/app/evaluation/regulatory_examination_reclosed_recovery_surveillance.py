from __future__ import annotations
import hashlib, json


def version_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def surveillance_score(payload: dict) -> dict:
    baseline = float(payload.get("closure_residual_risk_score", 0.0))
    current = float(payload.get("current_systemic_risk_score", baseline))
    control_baseline = float(payload.get("closure_control_effectiveness", 100.0))
    control_current = float(payload.get("current_control_effectiveness", control_baseline))
    expected = set(payload.get("expected_entity_ids", []))
    regressed = set(payload.get("regressed_entity_ids", []))
    rebound = max(0.0, current - baseline)
    rebound_pct = 0.0 if baseline <= 0 else round(100.0 * rebound / baseline, 2)
    decay = max(0.0, control_baseline - control_current)
    regression_pct = 0.0 if not expected else round(100.0 * len(expected & regressed) / len(expected), 2)
    signals = []
    if rebound_pct >= float(payload.get("risk_rebound_threshold_percent", 20.0)): signals.append("systemic_risk_rebound")
    if decay >= float(payload.get("control_decay_threshold_points", 10.0)): signals.append("recovery_effectiveness_decay")
    if regressed: signals.append("cross_entity_regression")
    if payload.get("new_examination_match"): signals.append("new_examination_match")
    if payload.get("regulator_follow_up_adverse"): signals.append("adverse_regulator_follow_up")
    return {
        "systemic_risk_rebound_percent": rebound_pct,
        "recovery_effectiveness_decay_points": round(decay, 2),
        "cross_entity_regression_percent": regression_pct,
        "signals": signals,
        "sustainability_breach_candidate": bool(signals),
        "human_investigation_required": bool(signals),
    }


def reopening_readiness(payload: dict) -> dict:
    blockers=[]
    if not payload.get("sustainability_breach_confirmed"): blockers.append("sustainability_breach_not_confirmed")
    if not payload.get("investigation_complete"): blockers.append("investigation_incomplete")
    if not payload.get("independent_reassessment_complete"): blockers.append("independent_reassessment_incomplete")
    if not payload.get("executive_review_complete"): blockers.append("executive_review_incomplete")
    if not payload.get("internal_audit_review_complete"): blockers.append("internal_audit_review_incomplete")
    if not payload.get("prior_certification_compared"): blockers.append("prior_certification_not_compared")
    if not payload.get("renewed_remediation_candidate_prepared"): blockers.append("renewed_remediation_candidate_missing")
    return {
        "reopening_readiness_score": round(100.0 * (7-len(blockers))/7, 2),
        "ready_for_human_enterprise_reopening": not blockers,
        "blockers": blockers,
    }


def examination_match_score(payload: dict) -> dict:
    root = float(payload.get("root_cause_similarity", 0.0))
    controls = float(payload.get("control_overlap", 0.0))
    entities = float(payload.get("entity_overlap", 0.0))
    obligations = float(payload.get("regulatory_obligation_overlap", 0.0))
    score = round((root * .35 + controls * .30 + entities * .15 + obligations * .20) * 100.0, 2)
    return {"match_score": score, "closed_program_match_candidate": score >= float(payload.get("match_threshold", 70.0)), "human_validation_required": True}
