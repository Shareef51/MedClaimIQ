from app.domain.regulatory_examination_supervisory_reauthorized_recovery_outcome_validation import (
    SUPERVISORY_REAUTHORIZED_RECOVERY_OUTCOME_AUTHORITY,
    supervisory_reauthorized_recovery_outcome_contract,
)
from app.evaluation.regulatory_examination_supervisory_reauthorized_recovery_outcome_validation import (
    cross_entity_retransformation_completion,
    independent_recovery_outcome_assurance,
    reclosure_readiness,
    repeated_failure_control_effectiveness,
    sustainability_assessment,
    systemic_risk_reduction,
)
from app.services.regulatory_examination_supervisory_reauthorized_recovery_outcome_validation import RegulatoryExaminationSupervisoryReauthorizedRecoveryOutcomeValidationService


def test_release93_non_delegable_authority():
    a = SUPERVISORY_REAUTHORIZED_RECOVERY_OUTCOME_AUTHORITY
    assert a["release92_supervisory_execution_reference_required"]
    assert a["release92_independent_assurance_reference_required"]
    assert a["independent_outcome_validation_required"]
    assert not a["ai_can_accept_residual_systemic_risk"]
    assert not a["ai_can_certify_recovery_effectiveness"]
    assert not a["ai_can_recertify_recovery"]
    assert not a["ai_can_reclose_program"]
    assert not a["worker_can_reclose_program"]


def test_release93_retransformation_risk_and_cross_entity_validation():
    risk = systemic_risk_reduction({"release92_baseline_systemic_risk_score": 96, "current_systemic_risk_score": 48, "minimum_required_reduction_percent": 35})
    assert risk["risk_reduction_percent"] == 50.0 and risk["risk_reduction_target_met"]
    repeated = repeated_failure_control_effectiveness({"controls": [
        {"control_id": "c1", "failure_count": 4, "result": "pass", "evidence_refs": ["e1"], "independent_tested": True, "release92_execution_reference": "ex92"},
        {"control_id": "c2", "repeated_failure": True, "effectiveness": "stable", "evidence_refs": ["e2"], "independent_tested": True, "release92_execution_reference": "ex92"},
    ]})
    assert repeated["repeated_failure_controls_effective"] and repeated["independently_validated_effective_count"] == 2
    entities = cross_entity_retransformation_completion({"entities": [
        {"entity_id": "US", "status": "complete", "evidence_refs": ["e1"], "control_retransformation_validated": True, "release92_execution_reference": "ex92"},
        {"entity_id": "EU", "status": "validated", "evidence_refs": ["e2"], "control_retransformation_validated": True, "release92_execution_reference": "ex92"},
    ]})
    assert entities["cross_entity_retransformation_completion_reconciled"]


def test_release93_independent_sustainability_and_readiness():
    iv = independent_recovery_outcome_assurance({"tests": [
        {"result": "pass", "independent_reviewer_id": "ia1", "evidence_refs": ["ev1"], "release92_execution_scope_validated": True, "cross_entity_effectiveness_validated": True, "repeated_failure_scope_validated": True},
        {"result": "effective", "independent_reviewer_id": "ia2", "evidence_refs": ["ev2"], "release92_execution_scope_validated": True, "cross_entity_effectiveness_validated": True, "repeated_failure_scope_validated": True},
    ]})
    assert iv["independent_recovery_outcome_validated"] and not iv["automated_certification_allowed"]
    sustain = sustainability_assessment({"observed_window_days": 120, "minimum_window_days": 90, "minimum_control_health_score": 88, "observations": [
        {"status": "stable", "control_health_score": 94, "release92_execution_reference": "ex92"},
        {"status": "stable", "control_health_score": 91, "release92_execution_reference": "ex92"},
    ]})
    assert sustain["sustainability_assurance_passed"]
    ready = reclosure_readiness({
        "release92_supervisory_execution_reference_present": True,
        "release92_independent_assurance_reference_present": True,
        "supervisory_recovery_outcomes_complete": True,
        "cross_entity_retransformation_completion_reconciled": True,
        "repeated_failure_controls_effective": True,
        "independent_recovery_outcome_validated": True,
        "systemic_risk_reduction_verified": True,
        "unresolved_blockers_cleared": True,
        "regulatory_commitments_reconciled": True,
        "sustainability_window_passed": True,
        "residual_risk_human_decision_recorded": True,
    })
    assert ready["ready_for_executive_recertification"] and ready["reclosure_readiness_score"] == 100.0


def test_release93_human_recertification_and_reclosure_boundaries():
    svc = RegulatoryExaminationSupervisoryReauthorizedRecoveryOutcomeValidationService(None, "tenant-a")
    try:
        svc.residual_risk_reassessment("ai", {"actor_role": "ai_agent", "decision": "accept", "release92_supervisory_recovery_execution_version_id": "ex92", "residual_systemic_risk_score": 7, "rationale": "x"})
    except PermissionError:
        pass
    else:
        raise AssertionError("AI cannot accept residual systemic risk")
    try:
        svc.reclose_program("ai", {"actor_role": "ai_agent", "decision": "reclose", "recovery_recertification_version_id": "rr93", "rationale": "x"})
    except PermissionError:
        pass
    else:
        raise AssertionError("AI cannot reclose program")
    cert = svc.recertify_recovery("cro", {
        "actor_role": "chief_risk_officer",
        "decision": "recertify",
        "release92_supervisory_recovery_execution_version_id": "ex92",
        "release92_independent_recovery_assurance_version_id": "ia92",
        "independent_outcome_validation_version_id": "iv93",
        "residual_risk_decision_version_id": "rv93",
        "sustainability_assessment_version_id": "sv93",
        "rationale": "evidence complete",
    })
    assert cert["human_decision"] and not cert["automated_recertification"]
    closed = svc.reclose_program("cro", {"actor_role": "chief_risk_officer", "decision": "reclose", "recovery_recertification_version_id": cert["supervisory_recovery_recertification_version_id"], "rationale": "sustainability demonstrated"})
    assert closed["human_decision"] and not closed["automated_reclosure"]
    assert "Release 92 supervisory execution" in supervisory_reauthorized_recovery_outcome_contract()["traceability"]
