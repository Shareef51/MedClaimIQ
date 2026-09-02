from __future__ import annotations
import hashlib
import json


def version_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()


def supervisory_recovery_outcomes(payload: dict) -> dict:
    workstreams = payload.get("workstreams", [])
    controls = payload.get("controls", [])
    completed = [w for w in workstreams if str(w.get("status", "")).lower() in {"complete", "completed", "done"} and bool(w.get("completion_evidence_refs"))]
    blocked = [w for w in workstreams if str(w.get("status", "")).lower() in {"blocked", "overdue", "failed"}]
    transformed = [c for c in controls if str(c.get("action", "")).lower() in {"replace", "replacement", "redesign", "retransform", "re-transform", "re-transformation"}]
    effective = [c for c in transformed if str(c.get("effectiveness", c.get("result", ""))).lower() in {"effective", "pass", "passed", "stable"} and bool(c.get("evidence_refs"))]
    failed = [c for c in transformed if str(c.get("effectiveness", c.get("result", ""))).lower() in {"ineffective", "fail", "failed", "degraded"}]
    release92_bound = all(bool(x.get("release92_execution_reference")) for x in completed + transformed) if completed or transformed else False
    return {
        "workstream_count": len(workstreams),
        "completed_evidence_bound_workstream_count": len(completed),
        "blocked_workstream_count": len(blocked),
        "control_retransformation_count": len(transformed),
        "validated_effective_retransformation_count": len(effective),
        "failed_or_degraded_retransformation_count": len(failed),
        "release92_execution_provenance_complete": release92_bound,
        "supervisory_recovery_outcomes_complete": bool(workstreams or transformed) and len(completed) == len(workstreams) and not blocked and len(effective) == len(transformed) and not failed and release92_bound,
        "human_interpretation_required": True,
    }


def systemic_risk_reduction(payload: dict) -> dict:
    baseline = float(payload.get("release92_baseline_systemic_risk_score", payload.get("baseline_systemic_risk_score", 0)) or 0)
    current = float(payload.get("current_systemic_risk_score", 0) or 0)
    reduction = round(max(0.0, baseline - current), 2)
    pct = round(reduction / baseline * 100, 2) if baseline > 0 else 0.0
    target = float(payload.get("minimum_required_reduction_percent", 35) or 35)
    rebound = current > baseline
    return {
        "release92_baseline_systemic_risk_score": baseline,
        "current_systemic_risk_score": current,
        "absolute_risk_reduction": reduction,
        "risk_reduction_percent": pct,
        "minimum_required_reduction_percent": target,
        "risk_reduction_target_met": baseline > 0 and pct >= target and not rebound,
        "systemic_risk_rebound": rebound,
        "human_residual_risk_reassessment_required": True,
    }


def cross_entity_retransformation_completion(payload: dict) -> dict:
    entities = payload.get("entities", [])
    complete, incomplete, missing = [], [], []
    for e in entities:
        eid = str(e.get("entity_id", ""))
        status_ok = str(e.get("status", "")).lower() in {"complete", "completed", "effective", "validated"}
        evidence_ok = bool(e.get("evidence_refs"))
        retransformation_ok = e.get("control_retransformation_validated") is True
        release92_ok = bool(e.get("release92_execution_reference"))
        if status_ok and evidence_ok and retransformation_ok and release92_ok:
            complete.append(eid)
        else:
            incomplete.append(eid)
        if not evidence_ok:
            missing.append(eid)
    return {
        "entity_count": len(entities),
        "completed_entity_ids": sorted(x for x in complete if x),
        "incomplete_entity_ids": sorted(x for x in incomplete if x),
        "missing_evidence_entity_ids": sorted(x for x in missing if x),
        "cross_entity_retransformation_completion_reconciled": bool(entities) and not incomplete and not missing,
    }


def repeated_failure_control_effectiveness(payload: dict) -> dict:
    controls = payload.get("controls", [])
    scoped = [c for c in controls if bool(c.get("repeated_failure")) or int(c.get("failure_count", 0) or 0) >= 2]
    passed = [c for c in scoped if str(c.get("result", c.get("effectiveness", ""))).lower() in {"pass", "passed", "effective", "stable"} and bool(c.get("evidence_refs")) and c.get("independent_tested") is True and bool(c.get("release92_execution_reference"))]
    failed = [c for c in scoped if str(c.get("result", c.get("effectiveness", ""))).lower() in {"fail", "failed", "ineffective", "degraded"}]
    return {
        "repeated_failure_control_count": len(scoped),
        "independently_validated_effective_count": len(passed),
        "failed_or_degraded_count": len(failed),
        "repeated_failure_controls_effective": bool(scoped) and len(scoped) == len(passed) and not failed,
        "human_certification_required": True,
        "automated_certification_allowed": False,
    }


def independent_recovery_outcome_assurance(payload: dict) -> dict:
    tests = payload.get("tests", [])
    failed = [t for t in tests if str(t.get("result", "")).lower() in {"fail", "failed", "ineffective", "degraded"}]
    independent = all(bool(t.get("independent_reviewer_id")) for t in tests) if tests else False
    evidence = all(bool(t.get("evidence_refs")) for t in tests) if tests else False
    release92_scope = all(t.get("release92_execution_scope_validated") is True for t in tests) if tests else False
    cross_entity = all(t.get("cross_entity_effectiveness_validated") is True for t in tests) if tests else False
    repeated = all(t.get("repeated_failure_scope_validated") is True for t in tests) if tests else False
    return {
        "test_count": len(tests),
        "failed_test_count": len(failed),
        "independence_complete": independent,
        "evidence_complete": evidence,
        "release92_execution_scope_validated": release92_scope,
        "cross_entity_effectiveness_validated": cross_entity,
        "repeated_failure_scope_validated": repeated,
        "independent_recovery_outcome_validated": bool(tests) and not failed and independent and evidence and release92_scope and cross_entity and repeated,
        "human_certification_required": True,
        "automated_certification_allowed": False,
    }


def regulatory_commitment_completion(payload: dict) -> dict:
    commitments = payload.get("commitments", [])
    completed, unresolved = [], []
    for c in commitments:
        cid = str(c.get("commitment_id", ""))
        evidence_ok = bool(c.get("completion_evidence_refs"))
        release92_ok = bool(c.get("release92_execution_reference"))
        implementation_ok = str(c.get("implementation_status", c.get("status", ""))).lower() in {"complete", "completed", "fulfilled"}
        (completed if implementation_ok and evidence_ok and release92_ok else unresolved).append(cid)
    return {
        "commitment_count": len(commitments),
        "implemented_commitment_ids": sorted(x for x in completed if x),
        "unresolved_commitment_ids": sorted(x for x in unresolved if x),
        "commitment_implementation_reconciled": not unresolved,
        "human_commitment_closure_required": True,
        "automated_commitment_closure_allowed": False,
    }


def blocker_governance(payload: dict) -> dict:
    blockers = payload.get("blockers", [])
    unresolved = [b for b in blockers if str(b.get("status", "open")).lower() not in {"resolved", "closed", "cleared"}]
    material = [b for b in unresolved if str(b.get("severity", "")).lower() in {"high", "critical", "material"}]
    stale = [b for b in blockers if b.get("evidence_fresh") is False]
    return {
        "blocker_count": len(blockers),
        "unresolved_blocker_count": len(unresolved),
        "material_unresolved_blocker_count": len(material),
        "stale_evidence_blocker_count": len(stale),
        "unresolved_blockers_cleared": not unresolved and not stale,
        "executive_escalation_required": bool(material),
    }


def sustainability_assessment(payload: dict) -> dict:
    obs = payload.get("observations", [])
    minimum_days = int(payload.get("minimum_window_days", 90) or 90)
    observed_days = int(payload.get("observed_window_days", 0) or 0)
    breaches = [o for o in obs if bool(o.get("breach")) or str(o.get("status", "")).lower() in {"failed", "degraded", "unstable", "regressed"}]
    health = [float(o.get("control_health_score")) for o in obs if o.get("control_health_score") is not None]
    minimum_health = min(health) if health else 0.0
    required = float(payload.get("minimum_control_health_score", 88) or 88)
    release92_refs = all(bool(o.get("release92_execution_reference")) for o in obs) if obs else False
    stable = observed_days >= minimum_days and bool(obs) and not breaches and minimum_health >= required and release92_refs
    return {
        "observation_count": len(obs),
        "observed_window_days": observed_days,
        "minimum_window_days": minimum_days,
        "breach_count": len(breaches),
        "minimum_observed_control_health_score": round(minimum_health, 2),
        "minimum_required_control_health_score": required,
        "release92_execution_provenance_complete": release92_refs,
        "control_health_stabilized": stable,
        "sustainability_window_complete": observed_days >= minimum_days,
        "sustainability_assurance_passed": stable,
        "human_reclosure_required": True,
    }


def reclosure_readiness(payload: dict) -> dict:
    checks = {
        "release92_supervisory_execution_reference_present": bool(payload.get("release92_supervisory_execution_reference_present")),
        "release92_independent_assurance_reference_present": bool(payload.get("release92_independent_assurance_reference_present")),
        "supervisory_recovery_outcomes_complete": bool(payload.get("supervisory_recovery_outcomes_complete")),
        "cross_entity_retransformation_completion_reconciled": bool(payload.get("cross_entity_retransformation_completion_reconciled")),
        "repeated_failure_controls_effective": bool(payload.get("repeated_failure_controls_effective")),
        "independent_recovery_outcome_validated": bool(payload.get("independent_recovery_outcome_validated")),
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
