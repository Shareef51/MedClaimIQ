from __future__ import annotations
import hashlib, json


def version_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def outcome_measurement(payload: dict) -> dict:
    baseline = float(payload.get("baseline_risk_score", 0.0))
    current = float(payload.get("current_risk_score", baseline))
    tests = payload.get("independent_tests", [])
    passed = sum(1 for t in tests if t.get("result") == "pass")
    test_pass_rate = 0.0 if not tests else round(100.0 * passed / len(tests), 2)
    expected = set(payload.get("expected_entity_ids", []))
    completed = set(payload.get("completed_entity_ids", []))
    entity_coverage = 100.0 if not expected else round(100.0 * len(expected & completed) / len(expected), 2)
    reduction = max(0.0, baseline-current)
    reduction_pct = 0.0 if baseline <= 0 else round(100.0 * reduction / baseline, 2)
    return {
        "baseline_risk_score": baseline,
        "current_risk_score": current,
        "risk_reduction_percent": reduction_pct,
        "independent_test_pass_rate": test_pass_rate,
        "cross_entity_completion_percent": entity_coverage,
        "recovery_effective_candidate": reduction_pct > 0 and test_pass_rate == 100.0 and entity_coverage == 100.0,
        "human_certification_required": True,
    }


def reclosure_readiness(payload: dict) -> dict:
    blockers=[]
    if not payload.get("all_workstreams_complete"): blockers.append("workstreams_incomplete")
    if not payload.get("implementation_evidence_complete"): blockers.append("implementation_evidence_incomplete")
    if not payload.get("independent_recovery_validation_passed"): blockers.append("independent_recovery_validation_not_passed")
    if not payload.get("cross_entity_reconciliation_complete"): blockers.append("cross_entity_reconciliation_incomplete")
    if not payload.get("regulatory_commitments_reconciled"): blockers.append("regulatory_commitments_unreconciled")
    if payload.get("unresolved_blockers", 0): blockers.append("unresolved_blockers")
    if not payload.get("sustainability_window_complete"): blockers.append("sustainability_window_incomplete")
    if not payload.get("residual_risk_human_accepted"): blockers.append("residual_risk_not_human_accepted")
    return {"reclosure_readiness_score": round(100.0 * (8-len(blockers))/8, 2), "ready_for_human_executive_reclosure": not blockers, "blockers": blockers}


def sustainability_status(payload: dict) -> dict:
    observations = payload.get("observations", [])
    failures = [x for x in observations if x.get("control_health") in {"degraded","failed"} or x.get("recurrence_detected")]
    return {
        "observation_count": len(observations),
        "adverse_observation_count": len(failures),
        "sustainability_passed": bool(observations) and not failures,
        "reopen_candidate": bool(failures),
        "human_reopening_required": bool(failures),
    }
