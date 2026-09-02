from __future__ import annotations

import hashlib
import json


def version_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()


def renewed_recovery_outcomes(payload: dict) -> dict:
    workstreams = payload.get("workstreams", [])
    controls = payload.get("controls", [])
    completed = [w for w in workstreams if str(w.get("status", "")).lower() in {"complete", "completed", "done"}]
    blocked = [w for w in workstreams if str(w.get("status", "")).lower() in {"blocked", "overdue", "failed"}]
    effective = [c for c in controls if str(c.get("effectiveness", "")).lower() in {"effective", "pass", "passed", "stable"}]
    failed = [c for c in controls if str(c.get("effectiveness", "")).lower() in {"ineffective", "fail", "failed", "degraded"}]
    return {
        "workstream_count": len(workstreams),
        "completed_workstream_count": len(completed),
        "blocked_workstream_count": len(blocked),
        "control_count": len(controls),
        "effective_control_count": len(effective),
        "failed_control_count": len(failed),
        "outcome_complete": bool(workstreams or controls) and not blocked and not failed,
        "human_interpretation_required": True,
    }


def systemic_risk_reduction(payload: dict) -> dict:
    baseline = float(payload.get("baseline_systemic_risk_score", 0) or 0)
    current = float(payload.get("current_systemic_risk_score", 0) or 0)
    absolute_reduction = round(max(0.0, baseline - current), 2)
    pct = round((absolute_reduction / baseline) * 100, 2) if baseline > 0 else 0.0
    target = float(payload.get("minimum_required_reduction_percent", 25) or 25)
    rebound = current > baseline
    return {
        "baseline_systemic_risk_score": baseline,
        "current_systemic_risk_score": current,
        "absolute_risk_reduction": absolute_reduction,
        "risk_reduction_percent": pct,
        "minimum_required_reduction_percent": target,
        "risk_reduction_target_met": baseline > 0 and pct >= target and not rebound,
        "systemic_risk_rebound": rebound,
        "human_residual_risk_reassessment_required": True,
    }


def cross_entity_completion(payload: dict) -> dict:
    entities = payload.get("entities", [])
    complete = []
    incomplete = []
    missing_evidence = []
    for e in entities:
        eid = str(e.get("entity_id", ""))
        status_ok = str(e.get("status", "")).lower() in {"complete", "completed", "effective", "validated"}
        evidence_ok = bool(e.get("evidence_refs"))
        (complete if status_ok and evidence_ok else incomplete).append(eid)
        if not evidence_ok:
            missing_evidence.append(eid)
    return {
        "entity_count": len(entities),
        "completed_entity_ids": sorted(x for x in complete if x),
        "incomplete_entity_ids": sorted(x for x in incomplete if x),
        "missing_evidence_entity_ids": sorted(x for x in missing_evidence if x),
        "cross_entity_completion_reconciled": bool(entities) and not incomplete and not missing_evidence,
    }


def independent_recovery_effectiveness(payload: dict) -> dict:
    tests = payload.get("tests", [])
    passed = [t for t in tests if str(t.get("result", "")).lower() in {"pass", "passed", "effective"}]
    failed = [t for t in tests if str(t.get("result", "")).lower() in {"fail", "failed", "ineffective"}]
    independent = all(bool(t.get("independent_reviewer_id")) for t in tests) if tests else False
    current_evidence = all(bool(t.get("evidence_refs")) for t in tests) if tests else False
    entities = sorted({str(e) for t in tests for e in t.get("entity_ids", []) if e})
    return {
        "test_count": len(tests),
        "passed_test_count": len(passed),
        "failed_test_count": len(failed),
        "validated_entity_ids": entities,
        "independence_complete": independent,
        "evidence_complete": current_evidence,
        "recovery_effectiveness_validated": bool(tests) and not failed and independent and current_evidence,
        "automated_certification_allowed": False,
        "human_certification_required": True,
    }


def regulatory_commitment_completion(payload: dict) -> dict:
    commitments = payload.get("commitments", [])
    completed = []
    unresolved = []
    for c in commitments:
        cid = str(c.get("commitment_id", ""))
        complete = str(c.get("status", "")).lower() in {"complete", "completed", "fulfilled"} and bool(c.get("completion_evidence_refs"))
        (completed if complete else unresolved).append(cid)
    return {
        "commitment_count": len(commitments),
        "completed_commitment_ids": sorted(x for x in completed if x),
        "unresolved_commitment_ids": sorted(x for x in unresolved if x),
        "commitment_completion_reconciled": not unresolved,
        "human_commitment_closure_required": True,
        "automated_commitment_closure_allowed": False,
    }


def sustainability_assessment(payload: dict) -> dict:
    observations = payload.get("observations", [])
    minimum_days = int(payload.get("minimum_window_days", 30) or 30)
    observed_days = int(payload.get("observed_window_days", 0) or 0)
    breaches = [o for o in observations if bool(o.get("breach")) or str(o.get("status", "")).lower() in {"failed", "degraded", "unstable"}]
    health_values = [float(o.get("control_health_score")) for o in observations if o.get("control_health_score") is not None]
    minimum_health = min(health_values) if health_values else 0.0
    required_health = float(payload.get("minimum_control_health_score", 80) or 80)
    stable = observed_days >= minimum_days and not breaches and bool(observations) and minimum_health >= required_health
    return {
        "observation_count": len(observations),
        "observed_window_days": observed_days,
        "minimum_window_days": minimum_days,
        "breach_count": len(breaches),
        "minimum_observed_control_health_score": round(minimum_health, 2),
        "minimum_required_control_health_score": required_health,
        "control_health_stabilized": stable,
        "sustainability_window_complete": observed_days >= minimum_days,
        "sustainability_assurance_passed": stable,
        "human_reclosure_required": True,
    }


def reclosure_readiness(payload: dict) -> dict:
    checks = {
        "renewed_recovery_outcomes_complete": bool(payload.get("renewed_recovery_outcomes_complete")),
        "cross_entity_completion_reconciled": bool(payload.get("cross_entity_completion_reconciled")),
        "independent_recovery_effectiveness_validated": bool(payload.get("independent_recovery_effectiveness_validated")),
        "systemic_risk_reduction_verified": bool(payload.get("systemic_risk_reduction_verified")),
        "unresolved_blockers_cleared": bool(payload.get("unresolved_blockers_cleared")),
        "regulatory_commitments_reconciled": bool(payload.get("regulatory_commitments_reconciled")),
        "sustainability_window_passed": bool(payload.get("sustainability_window_passed")),
        "residual_risk_human_decision_recorded": bool(payload.get("residual_risk_human_decision_recorded")),
    }
    blockers = [k for k, v in checks.items() if not v]
    score = round(sum(checks.values()) / len(checks) * 100, 2)
    return {
        "reclosure_readiness_score": score,
        "checks": checks,
        "blocking_items": blockers,
        "ready_for_executive_recertification": not blockers,
        "automated_recertification_allowed": False,
        "automated_reclosure_allowed": False,
    }
