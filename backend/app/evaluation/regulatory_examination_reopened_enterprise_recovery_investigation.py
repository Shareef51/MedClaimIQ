from __future__ import annotations
import hashlib
import json


def version_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()


def reconstruct_multi_cycle_enterprise_evidence(payload: dict) -> dict:
    cycles = sorted(payload.get("cycles", []), key=lambda x: (int(x.get("sequence", 0) or 0), str(x.get("cycle_id", ""))))
    adverse = {"failed", "recurred", "decayed", "reopened", "regressed", "breached", "ineffective", "systemic_failure"}
    failed = [c for c in cycles if str(c.get("status", "")).lower() in adverse]
    evidence = sorted({str(r) for c in cycles for r in c.get("evidence_refs", []) if r})
    missing = [str(c.get("cycle_id")) for c in cycles if c.get("cycle_id") and not c.get("evidence_refs")]
    reclosures = [c for c in cycles if bool(c.get("human_reclosure")) or c.get("reclosure_version_id")]
    reopenings = [c for c in cycles if bool(c.get("human_reopening")) or c.get("reopening_version_id")]
    assurance = [c for c in cycles if c.get("independent_assurance_version_id") or bool(c.get("independent_assurance_complete"))]
    authorizations = [c for c in cycles if c.get("human_reauthorization_version_id") or bool(c.get("human_reauthorization"))]
    return {
        "cycle_count": len(cycles),
        "failed_or_recurred_cycle_count": len(failed),
        "human_reclosure_count": len(reclosures),
        "human_reopening_count": len(reopenings),
        "independent_assurance_cycle_count": len(assurance),
        "human_reauthorization_cycle_count": len(authorizations),
        "evidence_refs": evidence,
        "unique_evidence_count": len(evidence),
        "cycles_missing_evidence": missing,
        "full_multi_cycle_enterprise_evidence_reconstructed": bool(cycles) and not missing,
        "repeated_enterprise_recovery_failure_pattern": len(failed) >= 2,
        "human_evidence_validation_required": True,
    }


def reconstruct_systemic_recovery_failure_root_causes(payload: dict) -> dict:
    prior = set(map(str, payload.get("prior_root_cause_ids", [])))
    historical = set(map(str, payload.get("historical_root_cause_ids", [])))
    current = set(map(str, payload.get("current_root_cause_ids", [])))
    persistent = sorted(current & (prior | historical))
    emergent = sorted(current - prior - historical)
    retired = sorted((prior | historical) - current)
    repeated_controls = int(payload.get("repeated_systemic_control_failure_count", 0) or 0)
    repeated_cycles = int(payload.get("repeated_recovery_failure_cycle_count", 0) or 0)
    rebound = bool(payload.get("systemic_risk_rebound_confirmed"))
    propagation = bool(payload.get("cross_entity_recurrence_confirmed"))
    commitment_breach = bool(payload.get("material_regulatory_commitment_breach_confirmed"))
    score = min(100.0, round(
        len(persistent)*20 + len(emergent)*10 + min(repeated_controls, 6)*7 + min(repeated_cycles, 5)*6 +
        (14 if rebound else 0) + (12 if propagation else 0) + (10 if commitment_breach else 0), 2
    ))
    return {
        "persistent_systemic_root_cause_ids": persistent,
        "emergent_systemic_root_cause_ids": emergent,
        "retired_root_cause_ids": retired,
        "systemic_recovery_failure_root_cause_risk_score": score,
        "persistent_systemic_root_cause_candidate": bool(persistent) and (repeated_controls > 0 or repeated_cycles >= 2 or rebound or propagation),
        "emergent_systemic_root_cause_candidate": bool(emergent) and (rebound or propagation or commitment_breach),
        "human_root_cause_confirmation_required": True,
        "automated_root_cause_conclusion_allowed": False,
    }


def validate_prior_enterprise_recertification_reclosure_assumptions(payload: dict) -> dict:
    assumptions = payload.get("assumptions", [])
    bad = {"breached", "invalid", "failed", "unsupported", "expired", "stale", "contradicted", "regressed"}
    good = {"valid", "confirmed", "sustained", "supported", "revalidated"}
    breached = [a for a in assumptions if str(a.get("current_status", a.get("status", "unknown"))).lower() in bad]
    unverified = [a for a in assumptions if str(a.get("current_status", a.get("status", "unknown"))).lower() not in bad | good]
    material = [a for a in assumptions if bool(a.get("material_change")) or bool(a.get("new_evidence_contradicts"))]
    return {
        "assumption_count": len(assumptions),
        "breached_assumption_ids": sorted(str(a.get("assumption_id")) for a in breached if a.get("assumption_id")),
        "unverified_assumption_ids": sorted(str(a.get("assumption_id")) for a in unverified if a.get("assumption_id")),
        "materially_changed_assumption_ids": sorted(str(a.get("assumption_id")) for a in material if a.get("assumption_id")),
        "prior_enterprise_recertification_reclosure_assumptions_at_risk": bool(breached or unverified or material),
        "human_assumption_validation_required": bool(breached or unverified or material),
    }


def analyze_repeated_systemic_control_retransformation_failures(payload: dict) -> dict:
    controls = payload.get("controls", [])
    failed = []
    for c in controls:
        status = str(c.get("status", "")).lower()
        if c.get("retransformation_effective") is False or c.get("independent_revalidation_passed") is False or status in {"failed", "regressed", "ineffective", "recurred", "breached"}:
            failed.append(c)
    repeated = sorted(str(c.get("control_id")) for c in failed if c.get("control_id") and int(c.get("failure_cycle_count", 0) or 0) >= 2)
    entities = sorted({str(e) for c in failed for e in c.get("entity_ids", []) if e})
    roots = sorted({str(r) for c in failed for r in c.get("root_cause_ids", []) if r})
    return {
        "control_count": len(controls),
        "failed_systemic_control_retransformation_count": len(failed),
        "repeated_failure_control_ids": repeated,
        "affected_entity_ids": entities,
        "linked_root_cause_ids": roots,
        "enterprise_systemic_control_failure_candidate": bool(repeated) or len(failed) >= 2 or len(entities) >= 2,
        "human_control_transformation_decision_required": bool(failed),
        "recommendation_only": True,
    }


def map_cross_entity_causal_propagation(payload: dict) -> dict:
    links = payload.get("causal_links", [])
    high = [x for x in links if float(x.get("confidence", 0) or 0) >= 0.75]
    systemic = [x for x in high if bool(x.get("shared_root_cause")) or bool(x.get("shared_control_failure")) or bool(x.get("propagation_evidence"))]
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
    linked_commitments = [x for x in commitments if bool(x.get("linked_to_reopened_enterprise_recovery")) or bool(x.get("linked_to_systemic_failure"))]
    breached = [x for x in linked_commitments if bool(x.get("breached")) or bool(x.get("overdue")) or str(x.get("status", "")).lower() in {"breached", "overdue", "failed"}]
    material_commitments = [x for x in linked_commitments if str(x.get("materiality", "low")).lower() in {"high", "critical"}]
    linked_followups = [x for x in followups if bool(x.get("linked_to_reopened_enterprise_recovery")) or bool(x.get("linked_to_systemic_failure"))]
    open_followups = [x for x in linked_followups if str(x.get("status", "open")).lower() not in {"closed", "resolved", "complete"}]
    material_followups = [x for x in linked_followups if bool(x.get("overdue")) or str(x.get("materiality", "low")).lower() in {"high", "critical"}]
    return {
        "commitment_count": len(commitments),
        "linked_commitment_count": len(linked_commitments),
        "breached_linked_commitment_count": len(breached),
        "material_linked_commitment_count": len(material_commitments),
        "followup_count": len(followups),
        "linked_followup_count": len(linked_followups),
        "open_linked_followup_count": len(open_followups),
        "material_linked_followup_count": len(material_followups),
        "material_regulatory_impact_candidate": bool(breached or material_commitments or material_followups),
        "human_regulatory_interpretation_required": bool(linked_commitments or linked_followups),
        "regulator_intent_inference_allowed": False,
    }


def classify_enterprise_systemic_failure(payload: dict) -> dict:
    root_score = float(payload.get("systemic_recovery_failure_root_cause_risk_score", 0) or 0)
    failed_controls = int(payload.get("failed_systemic_control_retransformation_count", 0) or 0)
    affected_entities = int(payload.get("affected_entity_count", 0) or 0)
    rebound = float(payload.get("systemic_risk_rebound_percent", 0) or 0)
    repeat_cycles = int(payload.get("repeated_failure_cycle_count", 0) or 0)
    breached_commitments = int(payload.get("breached_regulatory_commitment_count", 0) or 0)
    material_followups = int(payload.get("material_regulator_followup_count", 0) or 0)
    score = min(100.0, round(
        root_score*0.32 + min(failed_controls, 6)*7 + min(affected_entities, 8)*4 + min(rebound, 100)*0.14 +
        min(repeat_cycles, 6)*4 + min(breached_commitments, 4)*4 + min(material_followups, 4)*3,
        2,
    ))
    classification = "enterprise_critical" if score >= 78 else "enterprise_systemic" if score >= 58 else "material" if score >= 38 else "localized"
    return {
        "enterprise_systemic_failure_score": score,
        "proposed_enterprise_systemic_failure_classification": classification,
        "enterprise_systemic_failure_candidate": classification in {"enterprise_systemic", "enterprise_critical"},
        "executive_internal_audit_challenge_required": classification in {"enterprise_systemic", "enterprise_critical"},
        "human_classification_confirmation_required": True,
        "automated_authoritative_classification_allowed": False,
    }


def enterprise_remediation_reauthorization_readiness(payload: dict) -> dict:
    gates = {
        "release98_human_enterprise_reopening_verified": bool(payload.get("release98_human_enterprise_reopening_verified")),
        "formal_reopened_enterprise_investigation_complete": bool(payload.get("formal_reopened_enterprise_investigation_complete")),
        "full_multi_cycle_enterprise_evidence_reconstructed": bool(payload.get("full_multi_cycle_enterprise_evidence_reconstructed")),
        "prior_enterprise_recertification_reclosure_assumptions_validated": bool(payload.get("prior_enterprise_recertification_reclosure_assumptions_validated")),
        "persistent_emergent_systemic_root_causes_human_confirmed": bool(payload.get("persistent_emergent_systemic_root_causes_human_confirmed")),
        "repeated_systemic_control_retransformation_failure_assessed": bool(payload.get("repeated_systemic_control_retransformation_failure_assessed")),
        "cross_entity_causal_propagation_human_validated": bool(payload.get("cross_entity_causal_propagation_human_validated")),
        "regulatory_commitment_followup_impact_human_interpreted": bool(payload.get("regulatory_commitment_followup_impact_human_interpreted")),
        "enterprise_systemic_failure_classification_human_confirmed": bool(payload.get("enterprise_systemic_failure_classification_human_confirmed")),
        "renewed_enterprise_remediation_strategy_documented": bool(payload.get("renewed_enterprise_remediation_strategy_documented")),
        "independent_internal_audit_challenge_complete": bool(payload.get("independent_internal_audit_challenge_complete")),
        "segregation_of_duties_confirmed": bool(payload.get("segregation_of_duties_confirmed")),
        "executive_review_complete": bool(payload.get("executive_review_complete")),
        "evidence_bound_reauthorization_package_complete": bool(payload.get("evidence_bound_reauthorization_package_complete")),
    }
    blockers = [k for k, v in gates.items() if not v]
    score = round(100.0 * (len(gates)-len(blockers)) / len(gates), 2)
    return {
        "gates": gates,
        "blockers": blockers,
        "enterprise_remediation_reauthorization_readiness_score": score,
        "ready_for_human_enterprise_remediation_reauthorization": not blockers,
        "automated_reauthorization_allowed": False,
    }


def enterprise_recovery_investigation_dashboard(payload: dict) -> dict:
    return {
        "recovery_program_id": payload.get("recovery_program_id"),
        "investigation_status": payload.get("investigation_status", "open"),
        "systemic_root_cause_risk_score": float(payload.get("systemic_root_cause_risk_score", 0) or 0),
        "enterprise_systemic_failure_score": float(payload.get("enterprise_systemic_failure_score", 0) or 0),
        "affected_entity_count": int(payload.get("affected_entity_count", 0) or 0),
        "repeated_failure_control_count": int(payload.get("repeated_failure_control_count", 0) or 0),
        "breached_commitment_count": int(payload.get("breached_commitment_count", 0) or 0),
        "open_regulator_followup_count": int(payload.get("open_regulator_followup_count", 0) or 0),
        "human_reauthorization_pending": bool(payload.get("human_reauthorization_pending", True)),
        "monitoring_only": True,
    }


def audit_export_manifest(payload: dict) -> dict:
    refs = sorted({str(x) for x in payload.get("version_refs", []) if x})
    evidence = sorted({str(x) for x in payload.get("evidence_refs", []) if x})
    canonical = {"version_refs": refs, "evidence_refs": evidence, "recovery_program_id": payload.get("recovery_program_id")}
    return {**canonical, "version_ref_count": len(refs), "evidence_ref_count": len(evidence), "manifest_hash": version_hash(canonical), "human_authority_records_required": True}
