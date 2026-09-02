from __future__ import annotations
import hashlib, json


def version_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()


def compare_recurrence_root_causes(prior: dict, current: dict) -> dict:
    shared = sorted(set(prior.get("root_cause_ids", [])) & set(current.get("root_cause_ids", [])))
    prior_controls = set(prior.get("control_ids", [])); current_controls = set(current.get("control_ids", []))
    control_overlap = sorted(prior_controls & current_controls)
    same_primary = bool(prior.get("primary_root_cause_id")) and prior.get("primary_root_cause_id") == current.get("primary_root_cause_id")
    return {
        "same_primary_root_cause": same_primary,
        "shared_root_cause_ids": shared,
        "shared_control_ids": control_overlap,
        "recurrence_pattern_confirmed": same_primary or bool(shared),
        "human_review_required": True,
    }


def reclosure_readiness(payload: dict) -> dict:
    gates = {
        "renewed_plan_approved": bool(payload.get("renewed_plan_approved")),
        "all_milestones_complete": bool(payload.get("all_milestones_complete")),
        "cross_entity_propagation_complete": bool(payload.get("cross_entity_propagation_complete")),
        "regulator_follow_up_reconciled": bool(payload.get("regulator_follow_up_reconciled")),
        "independent_retest_passed": bool(payload.get("independent_retest_passed")),
        "independent_revalidation_complete": bool(payload.get("independent_revalidation_complete")),
        "evidence_sufficient": bool(payload.get("evidence_sufficient")),
        "sustainability_reset_ready": bool(payload.get("sustainability_reset_ready")),
        "second_recurrence_absent": not bool(payload.get("second_recurrence_detected")),
    }
    weights = {
        "renewed_plan_approved": 10,
        "all_milestones_complete": 15,
        "cross_entity_propagation_complete": 10,
        "regulator_follow_up_reconciled": 10,
        "independent_retest_passed": 15,
        "independent_revalidation_complete": 15,
        "evidence_sufficient": 10,
        "sustainability_reset_ready": 10,
        "second_recurrence_absent": 5,
    }
    score = sum(weights[k] for k, ok in gates.items() if ok)
    blockers = [k for k, ok in gates.items() if not ok]
    return {"score": score, "ready": score == 100, "gates": gates, "blockers": blockers, "human_recertification_required": True}


def second_recurrence_assessment(history: list[dict]) -> dict:
    recurrence_events = [x for x in history if x.get("event_type") in {"recurrence", "reopened", "control_failure"} and bool(x.get("confirmed", True))]
    second = len(recurrence_events) >= 2
    return {
        "recurrence_count": len(recurrence_events),
        "second_recurrence": second,
        "executive_escalation_required": second,
        "independent_reassessment_required": second,
    }


def sustainability_reset_window(payload: dict) -> dict:
    severity = str(payload.get("severity", "moderate")).lower()
    base_days = {"low": 60, "moderate": 90, "high": 180, "critical": 365}.get(severity, 90)
    recurrence_count = int(payload.get("recurrence_count", 1))
    extra = 90 if recurrence_count >= 2 else 0
    return {
        "minimum_monitoring_days": base_days + extra,
        "required_observation_count": 6 if severity in {"high", "critical"} or recurrence_count >= 2 else 3,
        "reset_required": True,
        "automatic_reclosure_allowed": False,
    }
