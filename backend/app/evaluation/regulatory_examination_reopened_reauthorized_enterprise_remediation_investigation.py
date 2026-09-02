from __future__ import annotations
import hashlib
import json


def version_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()


def reconstruct_multi_cycle_remediation_evidence(payload: dict) -> dict:
    cycles = sorted(payload.get("cycles", []), key=lambda x: (int(x.get("sequence", 0) or 0), str(x.get("cycle_id", ""))))
    adverse = {"failed", "recurred", "decayed", "reopened", "regressed", "breached", "ineffective", "systemic_failure", "remediation_failure"}
    failed = [c for c in cycles if str(c.get("status", "")).lower() in adverse]
    evidence = sorted({str(r) for c in cycles for r in c.get("evidence_refs", []) if r})
    missing = [str(c.get("cycle_id")) for c in cycles if c.get("cycle_id") and not c.get("evidence_refs")]
    treatments = [c for c in cycles if c.get("root_cause_treatment_version_id") or bool(c.get("root_cause_treatment_complete"))]
    assurances = [c for c in cycles if c.get("independent_assurance_version_id") or bool(c.get("independent_assurance_complete"))]
    reclosures = [c for c in cycles if c.get("sustainability_reclosure_version_id") or bool(c.get("human_reclosure"))]
    reopenings = [c for c in cycles if c.get("enterprise_reopening_version_id") or bool(c.get("human_reopening"))]
    return {
        "cycle_count": len(cycles),
        "failed_or_recurred_cycle_count": len(failed),
        "root_cause_treatment_cycle_count": len(treatments),
        "independent_assurance_cycle_count": len(assurances),
        "human_reclosure_count": len(reclosures),
        "human_reopening_count": len(reopenings),
        "evidence_refs": evidence,
        "unique_evidence_count": len(evidence),
        "cycles_missing_evidence": missing,
        "full_multi_cycle_remediation_evidence_reconstructed": bool(cycles) and not missing,
        "repeated_systemic_remediation_failure_pattern": len(failed) >= 2,
        "human_evidence_validation_required": True,
    }


def analyze_persistent_emergent_treatment_failure(payload: dict) -> dict:
    treatments = payload.get("treatments", [])
    failed, persistent, emergent, missing = [], [], [], []
    for t in treatments:
        tid = str(t.get("treatment_id", ""))
        status = str(t.get("current_status", t.get("status", "unknown"))).lower()
        failure = bool(t.get("treatment_failed")) or status in {"failed", "ineffective", "regressed", "recurred", "breached"}
        if failure:
            failed.append(tid)
            if str(t.get("root_cause_type", "persistent")).lower() == "emergent": emergent.append(tid)
            else: persistent.append(tid)
            if not t.get("evidence_refs"): missing.append(tid)
    total = max(1, len(treatments))
    failure_pct = round(100.0 * len(set(failed)) / total, 2)
    return {
        "treatment_count": len(treatments),
        "failed_treatment_ids": sorted(x for x in set(failed) if x),
        "failed_persistent_treatment_ids": sorted(x for x in set(persistent) if x),
        "failed_emergent_treatment_ids": sorted(x for x in set(emergent) if x),
        "missing_evidence_treatment_ids": sorted(x for x in set(missing) if x),
        "treatment_failure_percent": failure_pct,
        "material_root_cause_treatment_failure_candidate": failure_pct >= float(payload.get("material_failure_threshold_percent", 20) or 20) or bool(persistent),
        "human_treatment_failure_validation_required": bool(failed),
    }


def reconstruct_systemic_remediation_failure_root_causes(payload: dict) -> dict:
    prior = set(map(str, payload.get("prior_confirmed_root_cause_ids", [])))
    treated = set(map(str, payload.get("treated_root_cause_ids", [])))
    current = set(map(str, payload.get("current_root_cause_ids", [])))
    persistent = sorted(current & (prior | treated))
    emergent = sorted(current - prior - treated)
    retired = sorted((prior | treated) - current)
    failed_treatments = int(payload.get("failed_root_cause_treatment_count", 0) or 0)
    failed_controls = int(payload.get("repeated_systemic_control_failure_count", 0) or 0)
    failed_cycles = int(payload.get("repeated_remediation_failure_cycle_count", 0) or 0)
    rebound = bool(payload.get("systemic_risk_rebound_confirmed"))
    propagation = bool(payload.get("cross_entity_recurrence_confirmed"))
    commitment_breach = bool(payload.get("material_regulatory_commitment_breach_confirmed"))
    score = min(100.0, round(
        len(persistent) * 18 + len(emergent) * 10 + min(failed_treatments, 6) * 8 + min(failed_controls, 6) * 7
        + min(failed_cycles, 5) * 6 + (12 if rebound else 0) + (10 if propagation else 0) + (8 if commitment_breach else 0), 2
    ))
    return {
        "persistent_systemic_remediation_failure_root_cause_ids": persistent,
        "emergent_systemic_remediation_failure_root_cause_ids": emergent,
        "retired_root_cause_ids": retired,
        "systemic_remediation_failure_root_cause_risk_score": score,
        "persistent_systemic_root_cause_candidate": bool(persistent) and (failed_treatments > 0 or failed_controls > 0 or failed_cycles >= 2 or rebound),
        "emergent_systemic_root_cause_candidate": bool(emergent) and (rebound or propagation or commitment_breach),
        "human_root_cause_confirmation_required": True,
        "automated_root_cause_conclusion_allowed": False,
    }


def validate_prior_recertification_reclosure_assumptions(payload: dict) -> dict:
    assumptions = payload.get("assumptions", [])
    bad = {"breached", "invalid", "failed", "unsupported", "expired", "stale", "contradicted", "regressed"}
    good = {"valid", "confirmed", "sustained", "supported", "revalidated"}
    breached = [a for a in assumptions if str(a.get("current_status", a.get("status", "unknown"))).lower() in bad]
    unverified = [a for a in assumptions if str(a.get("current_status", a.get("status", "unknown"))).lower() not in bad | good]
    treatment_invalidated = [a for a in assumptions if bool(a.get("root_cause_treatment_invalidated")) or bool(a.get("control_retransformation_invalidated"))]
    return {
        "assumption_count": len(assumptions),
        "breached_assumption_ids": sorted(str(a.get("assumption_id")) for a in breached if a.get("assumption_id")),
        "unverified_assumption_ids": sorted(str(a.get("assumption_id")) for a in unverified if a.get("assumption_id")),
        "treatment_or_control_invalidated_assumption_ids": sorted(str(a.get("assumption_id")) for a in treatment_invalidated if a.get("assumption_id")),
        "prior_recertification_reclosure_assumptions_at_risk": bool(breached or unverified or treatment_invalidated),
        "human_assumption_validation_required": bool(breached or unverified or treatment_invalidated),
    }


def analyze_repeated_systemic_control_retransformation_failures(payload: dict) -> dict:
    controls = payload.get("controls", [])
    failed = []
    for c in controls:
        status = str(c.get("current_status", c.get("status", ""))).lower()
        if c.get("retransformation_effective") is False or c.get("independent_effectiveness_passed") is False or status in {"failed", "regressed", "ineffective", "recurred", "breached"}:
            failed.append(c)
    repeated = sorted(str(c.get("control_id")) for c in failed if c.get("control_id") and int(c.get("failure_cycle_count", 0) or 0) >= 2)
    entities = sorted({str(e) for c in failed for e in c.get("entity_ids", []) if e})
    roots = sorted({str(r) for c in failed for r in c.get("root_cause_ids", []) if r})
    treatments = sorted({str(t) for c in failed for t in c.get("root_cause_treatment_ids", []) if t})
    return {
        "control_count": len(controls),
        "failed_systemic_control_retransformation_count": len(failed),
        "repeated_failure_control_ids": repeated,
        "affected_entity_ids": entities,
        "linked_root_cause_ids": roots,
        "linked_root_cause_treatment_ids": treatments,
        "enterprise_systemic_control_failure_candidate": bool(repeated) or len(failed) >= 2 or len(entities) >= 2,
        "human_control_transformation_decision_required": bool(failed),
        "recommendation_only": True,
    }


def map_cross_entity_causal_propagation(payload: dict) -> dict:
    links = payload.get("causal_links", [])
    high = [x for x in links if float(x.get("confidence", 0) or 0) >= 0.75]
    systemic = [x for x in high if bool(x.get("shared_root_cause")) or bool(x.get("shared_treatment_failure")) or bool(x.get("shared_control_failure")) or bool(x.get("propagation_evidence"))]
    validated = [x for x in high if bool(x.get("human_validated"))]
    entities = sorted({str(v) for x in links for v in (x.get("source_entity_id"), x.get("target_entity_id")) if v})
    unvalidated = sorted(str(x.get("link_id")) for x in high if not x.get("human_validated") and x.get("link_id"))
    return {
        "causal_link_count": len(links),
        "high_confidence_link_count": len(high),
        "human_validated_high_confidence_link_count": len(validated),
        "systemic_propagation_link_count": len(systemic),
        "entity_ids": entities,
        "unvalidated_high_confidence_link_ids": unvalidated,
        "cross_entity_systemic_propagation_candidate": len(systemic) >= 1 and len(entities) >= 2,
        "human_validation_required": bool(unvalidated or systemic),
    }


def assess_regulatory_commitment_followup_impact(payload: dict) -> dict:
    commitments = payload.get("commitments", [])
    followups = payload.get("followups", [])
    linked_commitments = [x for x in commitments if bool(x.get("linked_to_reopened_remediation")) or bool(x.get("linked_to_systemic_remediation_failure"))]
    breached = [x for x in linked_commitments if bool(x.get("breached")) or bool(x.get("overdue")) or str(x.get("status", "")).lower() in {"breached", "overdue", "failed"}]
    material_commitments = [x for x in linked_commitments if str(x.get("materiality", "low")).lower() in {"high", "critical"}]
    linked_followups = [x for x in followups if bool(x.get("linked_to_reopened_remediation")) or bool(x.get("linked_to_systemic_remediation_failure"))]
    open_followups = [x for x in linked_followups if str(x.get("status", "open")).lower() not in {"closed", "resolved", "complete"}]
    material_followups = [x for x in linked_followups if bool(x.get("overdue")) or str(x.get("materiality", "low")).lower() in {"high", "critical"}]
    return {
        "linked_commitment_count": len(linked_commitments),
        "breached_linked_commitment_count": len(breached),
        "material_linked_commitment_count": len(material_commitments),
        "linked_followup_count": len(linked_followups),
        "open_linked_followup_count": len(open_followups),
        "material_linked_followup_count": len(material_followups),
        "material_regulatory_impact_candidate": bool(breached or material_commitments or material_followups),
        "human_regulatory_interpretation_required": bool(linked_commitments or linked_followups),
        "regulator_intent_inference_allowed": False,
    }


def classify_systemic_remediation_failure(payload: dict) -> dict:
    root_score = float(payload.get("systemic_remediation_failure_root_cause_risk_score", 0) or 0)
    failed_treatments = int(payload.get("failed_root_cause_treatment_count", 0) or 0)
    failed_controls = int(payload.get("failed_systemic_control_retransformation_count", 0) or 0)
    entities = int(payload.get("affected_entity_count", 0) or 0)
    rebound = float(payload.get("systemic_risk_rebound_percent", 0) or 0)
    cycles = int(payload.get("repeated_remediation_failure_cycle_count", 0) or 0)
    breached = int(payload.get("breached_regulatory_commitment_count", 0) or 0)
    followups = int(payload.get("material_regulator_followup_count", 0) or 0)
    score = min(100.0, round(root_score * .28 + min(failed_treatments, 6) * 6 + min(failed_controls, 6) * 6 + min(entities, 6) * 4 + min(rebound, 100) * .10 + min(cycles, 5) * 4 + min(breached, 4) * 4 + min(followups, 4) * 3, 2))
    classification = "enterprise_critical" if score >= 80 else "enterprise_systemic" if score >= 60 else "material" if score >= 35 else "localized"
    return {
        "systemic_remediation_failure_score": score,
        "proposed_systemic_remediation_failure_classification": classification,
        "enterprise_systemic_remediation_failure_candidate": score >= 60,
        "human_classification_confirmation_required": True,
        "authoritative_classification": False,
    }


def enterprise_remediation_reauthorization_readiness(payload: dict) -> dict:
    checks = {
        "release102_human_enterprise_reopening_verified": bool(payload.get("release102_human_enterprise_reopening_verified")),
        "formal_reopened_remediation_investigation_complete": bool(payload.get("formal_reopened_remediation_investigation_complete")),
        "full_multi_cycle_remediation_evidence_reconstructed": bool(payload.get("full_multi_cycle_remediation_evidence_reconstructed")),
        "persistent_emergent_treatment_failure_human_validated": bool(payload.get("persistent_emergent_treatment_failure_human_validated")),
        "prior_recertification_reclosure_assumptions_validated": bool(payload.get("prior_recertification_reclosure_assumptions_validated")),
        "systemic_remediation_failure_root_causes_human_confirmed": bool(payload.get("systemic_remediation_failure_root_causes_human_confirmed")),
        "repeated_systemic_control_retransformation_failure_assessed": bool(payload.get("repeated_systemic_control_retransformation_failure_assessed")),
        "cross_entity_causal_propagation_human_validated": bool(payload.get("cross_entity_causal_propagation_human_validated")),
        "regulatory_commitment_followup_impact_human_interpreted": bool(payload.get("regulatory_commitment_followup_impact_human_interpreted")),
        "systemic_remediation_failure_classification_human_confirmed": bool(payload.get("systemic_remediation_failure_classification_human_confirmed")),
        "renewed_enterprise_remediation_strategy_documented": bool(payload.get("renewed_enterprise_remediation_strategy_documented")),
        "independent_internal_audit_challenge_complete": bool(payload.get("independent_internal_audit_challenge_complete")),
        "segregation_of_duties_confirmed": bool(payload.get("segregation_of_duties_confirmed")),
        "executive_review_complete": bool(payload.get("executive_review_complete")),
        "evidence_bound_reauthorization_package_complete": bool(payload.get("evidence_bound_reauthorization_package_complete")),
    }
    blockers = [k for k, ok in checks.items() if not ok]
    score = round(100.0 * sum(checks.values()) / len(checks), 2)
    return {
        "gates": checks,
        "blockers": blockers,
        "enterprise_remediation_reauthorization_readiness_score": score,
        "ready_for_human_enterprise_remediation_reauthorization": not blockers,
        "automated_reauthorization_allowed": False,
    }


def supervisory_dashboard_summary(payload: dict) -> dict:
    return {
        "recovery_program_id": payload.get("recovery_program_id"),
        "investigation_status": payload.get("investigation_status", "open"),
        "systemic_remediation_failure_root_cause_risk_score": float(payload.get("systemic_remediation_failure_root_cause_risk_score", 0) or 0),
        "systemic_remediation_failure_score": float(payload.get("systemic_remediation_failure_score", 0) or 0),
        "failed_root_cause_treatment_count": int(payload.get("failed_root_cause_treatment_count", 0) or 0),
        "failed_systemic_control_count": int(payload.get("failed_systemic_control_count", 0) or 0),
        "affected_entity_count": int(payload.get("affected_entity_count", 0) or 0),
        "breached_commitment_count": int(payload.get("breached_commitment_count", 0) or 0),
        "human_reauthorization_pending": bool(payload.get("human_reauthorization_pending", True)),
        "decision_support_only": True,
    }


def audit_export_manifest(payload: dict) -> dict:
    refs = sorted(set(map(str, payload.get("version_refs", []))))
    evidence = sorted(set(map(str, payload.get("evidence_refs", []))))
    body = {"tenant_id": payload.get("tenant_id"), "recovery_program_id": payload.get("recovery_program_id"), "version_refs": refs, "evidence_refs": evidence}
    return {**body, "manifest_hash": version_hash(body), "immutable_export_manifest": True, "regulator_submission_authorized": False}
