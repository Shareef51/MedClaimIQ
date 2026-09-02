from app.domain.regulatory_examination_reauthorized_enterprise_remediation_reexecution_outcome_validation import (
    REAUTHORIZED_ENTERPRISE_REMEDIATION_REEXECUTION_OUTCOME_AUTHORITY,
    reauthorized_enterprise_remediation_reexecution_outcome_contract,
)
from app.evaluation.regulatory_examination_reauthorized_enterprise_remediation_reexecution_outcome_validation import (
    cross_entity_control_health,
    enterprise_control_completion,
    independent_enterprise_outcome_assurance,
    reclosure_readiness,
    repeated_failure_control_effectiveness,
    root_cause_treatment_effectiveness,
    sustainability_assessment,
    systemic_risk_reduction,
)
from app.services.regulatory_examination_reauthorized_enterprise_remediation_reexecution_outcome_validation import RegulatoryExaminationReauthorizedEnterpriseRemediationReExecutionOutcomeValidationService


def test_release105_non_delegable_authority():
    a = REAUTHORIZED_ENTERPRISE_REMEDIATION_REEXECUTION_OUTCOME_AUTHORITY
    assert a["release104_enterprise_remediation_reexecution_reference_required"]
    assert a["release104_independent_recovery_effectiveness_assurance_reference_required"]
    assert a["independent_outcome_assurance_required"]
    assert a["segregation_of_duties_required"]
    assert not a["ai_can_accept_residual_systemic_risk"]
    assert not a["ai_can_certify_recovery_effectiveness"]
    assert not a["ai_can_recertify_recovery"]
    assert not a["ai_can_reclose_program"]
    assert not a["worker_can_reclose_program"]


def test_release105_systemic_risk_enterprise_completion_and_repeated_failure_effectiveness():
    treatments = root_cause_treatment_effectiveness({"treatments": [
        {"treatment_id": "rc-persistent", "effectiveness": "effective", "evidence_refs": ["rt1"], "release104_remediation_reexecution_reference": "ex104", "release103_human_root_cause_confirmation_reference_present": True},
        {"treatment_id": "rc-emergent", "result": "passed", "evidence_refs": ["rt2"], "release104_remediation_reexecution_reference": "ex104", "release103_human_root_cause_confirmation_reference_present": True},
    ]})
    assert treatments["persistent_emergent_root_cause_treatments_effective"]
    risk = systemic_risk_reduction({"release104_baseline_systemic_risk_score": 100, "current_systemic_risk_score": 52, "minimum_required_reduction_percent": 40})
    assert risk["risk_reduction_percent"] == 48.0 and risk["risk_reduction_target_met"]
    controls = repeated_failure_control_effectiveness({"controls": [
        {"control_id": "c1", "failure_count": 5, "result": "pass", "evidence_refs": ["e1"], "independent_tested": True, "release104_remediation_reexecution_reference": "ex104", "release104_independent_recovery_effectiveness_assurance_reference": "ia104"},
        {"control_id": "c2", "repeated_failure": True, "effectiveness": "stable", "evidence_refs": ["e2"], "independent_tested": True, "release104_remediation_reexecution_reference": "ex104", "release104_independent_recovery_effectiveness_assurance_reference": "ia104"},
    ]})
    assert controls["repeated_failure_controls_effective"] and controls["independently_validated_effective_count"] == 2
    entities = enterprise_control_completion({"entities": [
        {"entity_id": "US", "status": "complete", "evidence_refs": ["e1"], "systemic_control_retransformation_validated": True, "human_control_approval_confirmed": True, "release104_remediation_reexecution_reference": "ex104"},
        {"entity_id": "EU", "status": "validated", "evidence_refs": ["e2"], "systemic_control_retransformation_validated": True, "human_control_approval_confirmed": True, "release104_remediation_reexecution_reference": "ex104"},
    ]})
    assert entities["enterprise_control_retransformation_completion_reconciled"]


def test_release105_independent_assurance_control_health_sustainability_and_readiness():
    iv = independent_enterprise_outcome_assurance({"tests": [
        {"result": "pass", "independent_reviewer_id": "ia1", "evidence_refs": ["ev1"], "release104_reexecution_scope_validated": True, "release104_independent_assurance_validated": True, "enterprise_wide_effectiveness_validated": True, "repeated_failure_scope_validated": True},
        {"result": "effective", "independent_reviewer_id": "ia2", "evidence_refs": ["ev2"], "release104_reexecution_scope_validated": True, "release104_independent_assurance_validated": True, "enterprise_wide_effectiveness_validated": True, "repeated_failure_scope_validated": True},
    ]})
    assert iv["independent_enterprise_recovery_outcome_validated"] and not iv["automated_certification_allowed"]
    health = cross_entity_control_health({"minimum_control_health_score": 90, "entities": [
        {"entity_id": "US", "control_health_score": 95, "status": "stable", "evidence_refs": ["ev1"], "release104_remediation_reexecution_reference": "ex104"},
        {"entity_id": "EU", "control_health_score": 92, "status": "stable", "evidence_refs": ["ev2"], "release104_remediation_reexecution_reference": "ex104"},
    ]})
    assert health["cross_entity_control_health_stabilized"]
    sustain = sustainability_assessment({"observed_window_days": 210, "minimum_window_days": 180, "minimum_control_health_score": 90, "observations": [
        {"status": "stable", "control_health_score": 95, "release104_remediation_reexecution_reference": "ex104", "release104_independent_recovery_effectiveness_assurance_reference": "ia104"},
        {"status": "stable", "control_health_score": 92, "release104_remediation_reexecution_reference": "ex104", "release104_independent_recovery_effectiveness_assurance_reference": "ia104"},
    ]})
    assert sustain["sustainability_assurance_passed"]
    ready = reclosure_readiness({
        "release104_enterprise_remediation_reexecution_reference_present": True,
        "release104_independent_recovery_effectiveness_assurance_reference_present": True,
        "enterprise_recovery_outcomes_complete": True,
        "persistent_emergent_root_cause_treatments_effective": True,
        "enterprise_control_retransformation_completion_reconciled": True,
        "repeated_failure_controls_effective": True,
        "independent_enterprise_recovery_outcome_validated": True,
        "systemic_risk_reduction_verified": True,
        "regulatory_commitments_reconciled": True,
        "unresolved_blockers_cleared": True,
        "cross_entity_control_health_stabilized": True,
        "sustainability_window_passed": True,
        "residual_risk_human_decision_recorded": True,
    })
    assert ready["ready_for_executive_systemic_recertification"] and ready["sustainability_reclosure_readiness_score"] == 100.0


def test_release105_human_recertification_reclosure_and_sod_boundaries():
    svc = RegulatoryExaminationReauthorizedEnterpriseRemediationReExecutionOutcomeValidationService(None, "tenant-a")
    try:
        svc.residual_risk_reassessment("ai", {"actor_role": "ai_agent", "decision": "accept", "release104_enterprise_remediation_reexecution_version_id": "ex104", "release104_independent_recovery_effectiveness_assurance_version_id": "ia104", "independent_outcome_validation_version_id": "iv105", "sustainability_assessment_version_id": "sv105", "residual_systemic_risk_score": 8, "rationale": "x", "evidence_refs": ["e"]})
    except PermissionError:
        pass
    else:
        raise AssertionError("AI cannot accept residual systemic risk")
    try:
        svc.independent_validate("owner-1", {"reviewer_role": "internal_auditor", "implementation_owner_id": "owner-1", "release104_enterprise_remediation_reexecution_version_id": "ex104", "release104_independent_recovery_effectiveness_assurance_version_id": "ia104", "tests": [{"result": "pass"}], "evidence_refs": ["e"]})
    except PermissionError:
        pass
    else:
        raise AssertionError("implementation owner cannot independently assure own work")
    try:
        svc.recertify_recovery("cro", {"actor_role": "chief_risk_officer", "decision": "recertify", "release104_enterprise_remediation_reexecution_version_id": "ex104", "release104_independent_recovery_effectiveness_assurance_version_id": "ia104", "independent_outcome_validation_version_id": "iv105", "residual_risk_decision_version_id": "rv105", "residual_risk_decision": "accept", "sustainability_assessment_version_id": "sv105", "reclosure_readiness_confirmed": False, "rationale": "x"})
    except ValueError:
        pass
    else:
        raise AssertionError("recertification cannot bypass deterministic readiness")
    cert = svc.recertify_recovery("cro", {
        "actor_role": "chief_risk_officer", "decision": "recertify",
        "release104_enterprise_remediation_reexecution_version_id": "ex104",
        "release104_independent_recovery_effectiveness_assurance_version_id": "ia104",
        "independent_outcome_validation_version_id": "iv105",
        "residual_risk_decision_version_id": "rv105", "residual_risk_decision": "accept",
        "sustainability_assessment_version_id": "sv105", "reclosure_readiness_confirmed": True,
        "rationale": "enterprise recovery evidence complete",
    })
    assert cert["human_decision"] and not cert["automated_recertification"]
    closed = svc.reclose_program("cro", {"actor_role": "chief_risk_officer", "decision": "reclose", "reauthorized_enterprise_remediation_reexecution_systemic_recovery_recertification_version_id": cert["reauthorized_enterprise_remediation_reexecution_systemic_recovery_recertification_version_id"], "sustainability_assurance_passed": True, "rationale": "sustained enterprise recovery demonstrated"})
    assert closed["human_decision"] and not closed["automated_reclosure"]
    assert "Release 104 reauthorized enterprise remediation re-execution" in reauthorized_enterprise_remediation_reexecution_outcome_contract()["traceability"]
