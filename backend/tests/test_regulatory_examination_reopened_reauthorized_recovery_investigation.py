from app.domain.regulatory_examination_reopened_reauthorized_recovery_investigation import (
    REOPENED_REAUTHORIZED_RECOVERY_INVESTIGATION_AUTHORITY,
    reopened_reauthorized_recovery_investigation_contract,
)
from app.evaluation.regulatory_examination_reopened_reauthorized_recovery_investigation import (
    reconstruct_reopened_recovery_cycles,
    reconstruct_repeated_failure_root_causes,
    reassess_prior_recertification_assumptions,
    analyze_re_rehabilitation_failures,
    recovery_reauthorization_readiness,
)
from app.services.regulatory_examination_reopened_reauthorized_recovery_investigation import RegulatoryExaminationReopenedReauthorizedRecoveryInvestigationService


def test_release91_non_delegable_authority():
    a = REOPENED_REAUTHORIZED_RECOVERY_INVESTIGATION_AUTHORITY
    assert not a["ai_can_authorize_recovery_remediation"]
    assert not a["ai_can_accept_residual_systemic_risk"]
    assert not a["ai_can_certify_recovery_effectiveness"]
    assert not a["worker_can_authorize_recovery_remediation"]
    assert a["release90_human_reopening_reference_required"]
    assert a["executive_reauthorization_required"]


def test_release91_multi_cycle_reconstruction_and_root_causes():
    evidence = reconstruct_reopened_recovery_cycles({"cycles": [
        {"cycle_id": "c1", "sequence": 1, "status": "failed", "evidence_refs": ["e1"], "reclosure_version_id": "cl1"},
        {"cycle_id": "c2", "sequence": 2, "status": "recurred", "evidence_refs": ["e2"], "reopening_version_id": "op2"},
    ]})
    assert evidence["repeated_failure_pattern"] and evidence["multi_cycle_evidence_complete"]
    roots = reconstruct_repeated_failure_root_causes({
        "prior_root_cause_ids": ["r1"], "historical_root_cause_ids": ["r1", "r0"], "current_root_cause_ids": ["r1", "r2"],
        "repeated_control_failure_count": 2, "systemic_risk_rebound_confirmed": True, "cross_entity_recurrence_confirmed": True,
    })
    assert roots["persistent_systemic_cause_candidate"] and roots["repeated_failure_root_cause_score"] >= 60
    assert roots["newly_emergent_root_cause_ids"] == ["r2"]


def test_release91_assumptions_rehabilitation_and_readiness():
    assumptions = reassess_prior_recertification_assumptions({"assumptions": [
        {"assumption_id": "a1", "current_status": "breached"}, {"assumption_id": "a2", "current_status": "confirmed"}
    ]})
    assert assumptions["prior_recertification_assumptions_at_risk"]
    rehab = analyze_re_rehabilitation_failures({"controls": [
        {"control_id": "ctrl1", "failure_cycle_count": 3, "re_rehabilitation_effective": False, "entity_ids": ["US"]},
        {"control_id": "ctrl2", "independent_revalidation_passed": False, "entity_ids": ["EU"]},
    ]})
    assert rehab["enterprise_re_rehabilitation_failure"] and "ctrl1" in rehab["repeated_failure_control_ids"]
    ready = recovery_reauthorization_readiness({
        "release90_human_reopening_verified": True,
        "multi_cycle_evidence_reconstructed": True,
        "prior_recertification_assumptions_reassessed": True,
        "repeated_failure_root_cause_human_confirmed": True,
        "cross_entity_causality_human_validated": True,
        "failed_re_rehabilitation_assessed": True,
        "regulator_followups_human_interpreted": True,
        "renewed_recovery_strategy_documented": True,
        "independent_internal_audit_challenge_complete": True,
        "executive_review_complete": True,
    })
    assert ready["ready_for_human_supervisory_reauthorization"] and ready["recovery_reauthorization_readiness_score"] == 100.0
    assert not ready["automated_reauthorization_allowed"]


def test_release91_release90_reopening_and_human_reauthorization_boundary():
    svc = RegulatoryExaminationReopenedReauthorizedRecoveryInvestigationService(None, "tenant-a")
    try:
        svc.create_investigation("ia", {"actor_role": "internal_auditor", "recovery_program_id": "rp1", "release90_reopening_version_id": "", "surveillance_version_refs": ["s1"], "evidence_refs": ["e1"]})
    except ValueError: pass
    else: raise AssertionError("Release 90 human reopening reference is mandatory")
    full = {
        "release90_human_reopening_verified": True, "multi_cycle_evidence_reconstructed": True,
        "prior_recertification_assumptions_reassessed": True, "repeated_failure_root_cause_human_confirmed": True,
        "cross_entity_causality_human_validated": True, "failed_re_rehabilitation_assessed": True,
        "regulator_followups_human_interpreted": True, "renewed_recovery_strategy_documented": True,
        "independent_internal_audit_challenge_complete": True, "executive_review_complete": True,
    }
    payload = {
        "actor_role": "ai_agent", "decision": "authorize", "recovery_program_id": "rp1",
        "release90_reopening_version_id": "op90", "investigation_version_id": "inv91", "investigation_conclusion_version_id": "con91",
        "strategy_candidate_version_id": "str91", "independent_challenge_version_id": "ch91", "rationale": "x", "readiness": full,
    }
    try: svc.authorize_recovery("ai", payload)
    except PermissionError: pass
    else: raise AssertionError("AI cannot reauthorize supervisory recovery remediation")
    payload["actor_role"] = "chief_risk_officer"
    authorized = svc.authorize_recovery("cro", payload)
    assert authorized["human_reauthorization"] and not authorized["automated_reauthorization"]
    assert "human supervisory recovery reauthorization" in reopened_reauthorized_recovery_investigation_contract()["traceability"]
