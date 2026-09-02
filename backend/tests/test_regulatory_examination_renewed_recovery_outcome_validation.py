from app.domain.regulatory_examination_renewed_recovery_outcome_validation import (
    RENEWED_RECOVERY_OUTCOME_AUTHORITY,
    renewed_recovery_outcome_contract,
)
from app.evaluation.regulatory_examination_renewed_recovery_outcome_validation import (
    cross_entity_completion,
    independent_recovery_effectiveness,
    reclosure_readiness,
    sustainability_assessment,
    systemic_risk_reduction,
)
from app.services.regulatory_examination_renewed_recovery_outcome_validation import RegulatoryExaminationRenewedRecoveryOutcomeValidationService


def test_release85_non_delegable_authority():
    authority = RENEWED_RECOVERY_OUTCOME_AUTHORITY
    assert authority["ai_can_accept_residual_systemic_risk"] is False
    assert authority["ai_can_certify_recovery_effectiveness"] is False
    assert authority["ai_can_recertify_recovery"] is False
    assert authority["ai_can_reclose_program"] is False
    assert authority["worker_can_reclose_program"] is False


def test_release85_risk_reduction_and_cross_entity_completion():
    risk = systemic_risk_reduction({"baseline_systemic_risk_score": 80, "current_systemic_risk_score": 40, "minimum_required_reduction_percent": 25})
    assert risk["risk_reduction_percent"] == 50.0 and risk["risk_reduction_target_met"]
    entities = cross_entity_completion({"entities": [{"entity_id": "US", "status": "complete", "evidence_refs": ["e1"]}, {"entity_id": "EU", "status": "complete", "evidence_refs": ["e2"]}]})
    assert entities["cross_entity_completion_reconciled"] and entities["completed_entity_ids"] == ["EU", "US"]


def test_release85_independent_validation_sustainability_and_readiness():
    validation = independent_recovery_effectiveness({"tests": [{"result": "pass", "independent_reviewer_id": "aud1", "entity_ids": ["US"], "evidence_refs": ["ev1"]}]})
    assert validation["recovery_effectiveness_validated"]
    sustainability = sustainability_assessment({"observed_window_days": 45, "minimum_window_days": 30, "minimum_control_health_score": 80, "observations": [{"status": "stable", "control_health_score": 92}]})
    assert sustainability["sustainability_assurance_passed"]
    ready = reclosure_readiness({
        "renewed_recovery_outcomes_complete": True,
        "cross_entity_completion_reconciled": True,
        "independent_recovery_effectiveness_validated": True,
        "systemic_risk_reduction_verified": True,
        "unresolved_blockers_cleared": True,
        "regulatory_commitments_reconciled": True,
        "sustainability_window_passed": True,
        "residual_risk_human_decision_recorded": True,
    })
    assert ready["ready_for_executive_recertification"] and ready["reclosure_readiness_score"] == 100


def test_release85_human_recertification_and_reclosure_boundaries():
    svc = RegulatoryExaminationRenewedRecoveryOutcomeValidationService(None, "tenant-a")
    try:
        svc.residual_risk_reassessment("ai", {"actor_role": "ai_agent", "decision": "accept", "residual_systemic_risk_score": 10, "rationale": "x"})
    except PermissionError:
        pass
    else:
        raise AssertionError("AI cannot accept residual systemic risk")
    try:
        svc.reclose_program("ai", {"actor_role": "ai_agent", "decision": "reclose", "recovery_recertification_version_id": "rr-1", "rationale": "x"})
    except PermissionError:
        pass
    else:
        raise AssertionError("AI cannot reclose the intervention program")
    assert "executive recertification" in renewed_recovery_outcome_contract()["traceability"]
