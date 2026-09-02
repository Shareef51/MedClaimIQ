from __future__ import annotations
import hashlib
import json


def version_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()


def enterprise_program_progress(payload: dict) -> dict:
    workstreams = payload.get("workstreams", [])
    total = len(workstreams)
    completed = [x for x in workstreams if str(x.get("status", "")).lower() in {"complete", "completed", "done"}]
    blocked = [x for x in workstreams if str(x.get("status", "")).lower() in {"blocked", "failed", "overdue"}]
    systemic = [x for x in workstreams if bool(x.get("systemic_scope")) or len(x.get("entity_ids", [])) >= 2]
    evidence_bound = [x for x in workstreams if x.get("evidence_refs")]
    release95_bound = [x for x in workstreams if x.get("release95_reauthorization_scope_reference")]
    progress = round(len(completed) / total * 100, 2) if total else 0.0
    return {
        "workstream_count": total,
        "completed_workstream_count": len(completed),
        "blocked_workstream_count": len(blocked),
        "systemic_workstream_count": len(systemic),
        "evidence_bound_workstream_count": len(evidence_bound),
        "release95_scope_bound_workstream_count": len(release95_bound),
        "progress_percent": progress,
        "executive_attention_required": bool(blocked),
    }


def systemic_control_retransformation_status(payload: dict) -> dict:
    controls = payload.get("controls", [])
    actions = {"replace", "replacement", "redesign", "retransform", "re-transform", "re-transformation", "retire-and-replace"}
    transformed = [c for c in controls if str(c.get("action", "")).lower() in actions]
    repeated = [c for c in controls if bool(c.get("repeated_failure")) or int(c.get("failure_cycle_count", c.get("failure_count", 0)) or 0) >= 2]
    systemic = [c for c in transformed if bool(c.get("systemic_scope")) or len(c.get("entity_ids", [])) >= 2]
    approved = [c for c in transformed if c.get("human_control_retransformation_approval_reference")]
    evidence = [c for c in transformed if c.get("implementation_evidence_refs")]
    missing_release95 = [c for c in transformed if not c.get("release95_reauthorization_scope_reference")]
    entities = sorted({str(e) for c in controls for e in c.get("entity_ids", []) if e})
    return {
        "control_count": len(controls),
        "repeated_failure_control_count": len(repeated),
        "systemic_retransformation_control_count": len(systemic),
        "replacement_or_retransformation_count": len(transformed),
        "human_approved_control_count": len(approved),
        "evidence_bound_control_count": len(evidence),
        "missing_release95_scope_reference_count": len(missing_release95),
        "affected_entity_ids": entities,
        "control_retransformation_ready": bool(transformed) and len(approved) == len(transformed) and not missing_release95,
        "automated_control_approval_allowed": False,
    }


def cross_entity_deployment_sequence(payload: dict) -> dict:
    steps = payload.get("deployment_steps", [])
    seq = [int(x.get("sequence", 0) or 0) for x in steps if x.get("sequence") is not None]
    duplicates = sorted({n for n in seq if seq.count(n) > 1})
    unsatisfied = [x for x in steps if x.get("dependency_ids") and not x.get("dependencies_satisfied", False)]
    blocked = [x for x in steps if str(x.get("status", "")).lower() in {"blocked", "failed", "overdue"}]
    missing_approval = [x for x in steps if not x.get("human_sequence_approval_reference")]
    missing_scope = [x for x in steps if not x.get("release95_reauthorization_scope_reference")]
    entities = sorted({str(e) for x in steps for e in x.get("entity_ids", []) if e})
    return {
        "deployment_step_count": len(steps),
        "entity_ids": entities,
        "cross_entity_scope": len(entities) >= 2,
        "duplicate_sequence_numbers": duplicates,
        "unsatisfied_dependency_count": len(unsatisfied),
        "blocked_step_count": len(blocked),
        "missing_human_sequence_approval_count": len(missing_approval),
        "missing_release95_scope_reference_count": len(missing_scope),
        "sequence_at_risk": bool(duplicates or unsatisfied or blocked or missing_approval or missing_scope),
    }


def regulatory_commitment_alignment(payload: dict) -> dict:
    commitments = payload.get("commitments", [])
    aligned = [c for c in commitments if c.get("mapped_recovery_workstream_id") and c.get("mapped_control_ids")]
    evidence_bound = [c for c in commitments if c.get("evidence_refs")]
    overdue = [c for c in commitments if str(c.get("status", "")).lower() in {"overdue", "breached", "missed"}]
    unconfirmed = [c for c in commitments if not c.get("human_commitment_owner_confirmation_reference")]
    ambiguous_regulator_intent = [c for c in commitments if c.get("requires_regulator_interpretation") and not c.get("human_regulatory_affairs_interpretation_reference")]
    return {
        "commitment_count": len(commitments),
        "aligned_commitment_count": len(aligned),
        "evidence_bound_commitment_count": len(evidence_bound),
        "overdue_or_breached_commitment_count": len(overdue),
        "missing_human_owner_confirmation_count": len(unconfirmed),
        "unresolved_regulator_interpretation_count": len(ambiguous_regulator_intent),
        "alignment_complete": bool(commitments) and len(aligned) == len(commitments) and not overdue and not unconfirmed and not ambiguous_regulator_intent,
        "automated_commitment_closure_allowed": False,
    }


def dependency_critical_path_assessment(payload: dict) -> dict:
    milestones = payload.get("milestones", [])
    critical = [m for m in milestones if m.get("critical_path") is True]
    blocked = [m for m in critical if str(m.get("status", "")).lower() in {"blocked", "failed", "overdue"}]
    unsatisfied = [m for m in critical if m.get("dependency_ids") and not m.get("dependencies_satisfied", False)]
    stale = [m for m in critical if not m.get("evidence_refs") or m.get("evidence_fresh") is False]
    cross_entity = [m for m in critical if len(m.get("entity_ids", [])) >= 2]
    return {
        "milestone_count": len(milestones),
        "critical_path_count": len(critical),
        "cross_entity_critical_path_count": len(cross_entity),
        "blocked_critical_count": len(blocked),
        "critical_dependency_gap_count": len(unsatisfied),
        "stale_or_missing_evidence_count": len(stale),
        "critical_path_at_risk": bool(blocked or unsatisfied or stale),
    }


def implementation_drift_detection(payload: dict) -> dict:
    planned = {str(x.get("control_id")): x for x in payload.get("planned_controls", []) if x.get("control_id")}
    actual = {str(x.get("control_id")): x for x in payload.get("implemented_controls", []) if x.get("control_id")}
    missing = sorted(set(planned) - set(actual))
    fingerprint_drift = sorted(k for k in set(planned) & set(actual) if str(planned[k].get("design_fingerprint", "")) != str(actual[k].get("design_fingerprint", "")))
    unauthorized = sorted(k for k, v in actual.items() if not v.get("human_control_retransformation_approval_reference"))
    out_of_scope = sorted(k for k, v in actual.items() if not v.get("release95_reauthorization_scope_reference"))
    entity_drift = sorted(k for k in set(planned) & set(actual) if set(map(str, planned[k].get("entity_ids", []))) != set(map(str, actual[k].get("entity_ids", []))))
    score = min(100, len(missing)*20 + len(fingerprint_drift)*25 + len(unauthorized)*30 + len(out_of_scope)*25 + len(entity_drift)*15)
    return {
        "missing_control_ids": missing,
        "design_drift_control_ids": fingerprint_drift,
        "entity_scope_drift_control_ids": entity_drift,
        "missing_human_approval_control_ids": unauthorized,
        "missing_release95_scope_control_ids": out_of_scope,
        "implementation_drift_score": score,
        "material_drift": score >= 50,
        "human_review_required": bool(missing or fingerprint_drift or entity_drift or unauthorized or out_of_scope),
    }


def systemic_recovery_kpi_assessment(payload: dict) -> dict:
    metrics = payload.get("metrics", [])
    breached, improved, evidence_bound, cross_entity = [], 0, 0, 0
    for m in metrics:
        actual, target, baseline = m.get("actual"), m.get("target"), m.get("baseline")
        direction = str(m.get("direction", "higher_is_better")).lower()
        if m.get("evidence_ref"): evidence_bound += 1
        if len(m.get("entity_ids", [])) >= 2 or m.get("enterprise_metric") is True: cross_entity += 1
        if actual is not None and baseline is not None:
            if (direction == "lower_is_better" and float(actual) < float(baseline)) or (direction != "lower_is_better" and float(actual) > float(baseline)):
                improved += 1
        if actual is not None and target is not None:
            fail = (direction == "lower_is_better" and float(actual) > float(target)) or (direction != "lower_is_better" and float(actual) < float(target))
            if fail: breached.append(m)
    score = round((len(metrics)-len(breached))/len(metrics)*100, 2) if metrics else 0.0
    return {
        "metric_count": len(metrics),
        "breached_metric_count": len(breached),
        "improved_vs_baseline_count": improved,
        "evidence_bound_metric_count": evidence_bound,
        "enterprise_or_cross_entity_metric_count": cross_entity,
        "systemic_recovery_kpi_score": score,
        "systemic_recovery_target_met": bool(metrics) and not breached and evidence_bound == len(metrics),
        "human_interpretation_required": True,
    }


def independent_effectiveness_assurance(payload: dict) -> dict:
    tests = payload.get("tests", [])
    failed = [t for t in tests if str(t.get("result", "")).lower() in {"fail", "failed", "ineffective", "regressed"}]
    independent = all(bool(t.get("independent_reviewer_id")) for t in tests) if tests else False
    evidence = all(bool(t.get("evidence_refs")) for t in tests) if tests else False
    release95 = all(t.get("release95_reauthorization_scope_validated") is True for t in tests) if tests else False
    repeated_failure = all(t.get("repeated_failure_scope_validated") is True for t in tests) if tests else False
    cross_entity = all(t.get("cross_entity_effectiveness_validated") is True for t in tests) if tests else False
    segregation = all(str(t.get("implementation_owner_id", "")) != str(t.get("independent_reviewer_id", "")) for t in tests) if tests else False
    entities = sorted({str(e) for t in tests for e in t.get("entity_ids", []) if e})
    return {
        "test_count": len(tests),
        "failed_test_count": len(failed),
        "validated_entity_ids": entities,
        "independence_complete": independent,
        "evidence_complete": evidence,
        "release95_reauthorization_scope_validated": release95,
        "repeated_failure_scope_validated": repeated_failure,
        "cross_entity_effectiveness_validated": cross_entity,
        "segregation_of_duties_satisfied": segregation,
        "assurance_passed": bool(tests) and not failed and independent and evidence and release95 and repeated_failure and cross_entity and segregation,
        "human_certification_required": True,
        "automated_certification_allowed": False,
    }


def enterprise_wide_control_validation(payload: dict) -> dict:
    validations = payload.get("control_validations", [])
    ineffective = [v for v in validations if str(v.get("status", "")).lower() in {"failed", "ineffective", "regressed", "partial"}]
    missing_entities = [v for v in validations if not v.get("entity_ids")]
    missing_evidence = [v for v in validations if not v.get("evidence_refs")]
    repeated_scope_missing = [v for v in validations if v.get("repeated_failure_control") and not v.get("repeated_failure_scope_validated")]
    entities = sorted({str(e) for v in validations for e in v.get("entity_ids", []) if e})
    controls = sorted({str(v.get("control_id")) for v in validations if v.get("control_id")})
    return {
        "validated_control_ids": controls,
        "validated_entity_ids": entities,
        "validation_count": len(validations),
        "ineffective_validation_count": len(ineffective),
        "missing_entity_scope_count": len(missing_entities),
        "missing_evidence_count": len(missing_evidence),
        "missing_repeated_failure_validation_count": len(repeated_scope_missing),
        "enterprise_validation_passed": bool(validations) and not ineffective and not missing_entities and not missing_evidence and not repeated_scope_missing and len(entities) >= 2,
        "human_effectiveness_certification_required": True,
    }


def blocker_escalation_assessment(payload: dict) -> dict:
    blockers = payload.get("blockers", [])
    material = [b for b in blockers if str(b.get("severity", "")).lower() in {"high", "critical", "material"}]
    overdue = [b for b in blockers if b.get("overdue") is True or str(b.get("status", "")).lower() in {"overdue", "breached"}]
    cross_entity = [b for b in blockers if len(b.get("entity_ids", [])) >= 2]
    regulatory = [b for b in blockers if b.get("regulatory_commitment_id") or b.get("regulator_followup_ref")]
    escalation = "executive_internal_audit" if material and (cross_entity or regulatory) else "executive" if material or overdue else "operational"
    return {
        "blocker_count": len(blockers),
        "material_blocker_count": len(material),
        "overdue_blocker_count": len(overdue),
        "cross_entity_blocker_count": len(cross_entity),
        "regulatory_linked_blocker_count": len(regulatory),
        "recommended_escalation_tier": escalation,
        "human_escalation_decision_required": bool(blockers),
        "automated_program_reclosure_allowed": False,
    }


def execution_readiness(payload: dict) -> dict:
    checks = {
        "release95_enterprise_reauthorization_reference_present": bool(payload.get("release95_enterprise_reauthorization_reference_present")),
        "release95_human_reauthorization_confirmed": bool(payload.get("release95_human_reauthorization_confirmed")),
        "enterprise_workstreams_defined": bool(payload.get("enterprise_workstreams_defined")),
        "systemic_control_retransformation_scope_human_approved": bool(payload.get("systemic_control_retransformation_scope_human_approved")),
        "cross_entity_deployment_sequence_validated": bool(payload.get("cross_entity_deployment_sequence_validated")),
        "regulatory_commitment_alignment_complete": bool(payload.get("regulatory_commitment_alignment_complete")),
        "critical_path_reviewed": bool(payload.get("critical_path_reviewed")),
        "implementation_evidence_current": bool(payload.get("implementation_evidence_current")),
        "systemic_recovery_kpis_baselined": bool(payload.get("systemic_recovery_kpis_baselined")),
        "independent_effectiveness_assurance_complete": bool(payload.get("independent_effectiveness_assurance_complete")),
        "enterprise_wide_control_validation_complete": bool(payload.get("enterprise_wide_control_validation_complete")),
        "material_blockers_resolved_or_human_escalated": bool(payload.get("material_blockers_resolved_or_human_escalated")),
    }
    blockers = [k for k,v in checks.items() if not v]
    return {
        "execution_readiness_score": round(sum(checks.values())/len(checks)*100, 2),
        "checks": checks,
        "blocking_items": blockers,
        "ready_for_human_recovery_outcome_review": not blockers,
        "automated_certification_allowed": False,
        "automated_risk_acceptance_allowed": False,
        "automated_commitment_closure_allowed": False,
        "automated_program_reclosure_allowed": False,
    }


def supervisory_dashboard_summary(payload: dict) -> dict:
    progress = enterprise_program_progress(payload)
    blockers = blocker_escalation_assessment(payload)
    kpis = systemic_recovery_kpi_assessment(payload)
    return {
        "progress": progress,
        "blockers": blockers,
        "systemic_recovery_kpis": kpis,
        "supervisory_attention_required": progress["executive_attention_required"] or blockers["recommended_escalation_tier"] != "operational" or not kpis["systemic_recovery_target_met"],
        "monitoring_only": True,
    }


def audit_export_manifest(payload: dict) -> dict:
    refs = sorted({str(x) for x in payload.get("version_refs", []) if x})
    evidence = sorted({str(x) for x in payload.get("evidence_refs", []) if x})
    body = {"version_refs": refs, "evidence_refs": evidence, "tenant_id": payload.get("tenant_id"), "recovery_program_id": payload.get("recovery_program_id")}
    return {
        **body,
        "manifest_hash": version_hash(body),
        "immutable_export": True,
        "human_submission_required": True,
    }
