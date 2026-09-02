from app.domain.regulatory_reopened_outcome_validation import REOPENED_OUTCOME_AUTHORITY
from app.evaluation.regulatory_reopened_outcome_validation import evaluate_reclosure_readiness, evaluate_traceability


def test_release62_non_delegable_reclosure_authority():
    assert REOPENED_OUTCOME_AUTHORITY["ai_can_reclose_finding"] is False
    assert REOPENED_OUTCOME_AUTHORITY["ai_can_recertify_control_effectiveness"] is False
    assert REOPENED_OUTCOME_AUTHORITY["ai_can_accept_residual_risk"] is False
    assert REOPENED_OUTCOME_AUTHORITY["worker_can_collect_or_move_money"] is False


def test_release62_ready_case_requires_all_gates():
    r = evaluate_reclosure_readiness({
        "current_effectiveness_score": 1.0,
        "recurrence_containment_score": 1.0,
        "independent_validated": True,
        "sustainability_complete": True,
        "cross_entity_complete": True,
        "commitments_complete": True,
        "second_recurrence_count": 0,
    })
    assert r["score"] == 100.0
    assert r["ready"] is True
    assert r["decision_authority"] == "human_only"


def test_release62_second_recurrence_blocks_reclosure():
    r = evaluate_reclosure_readiness({
        "current_effectiveness_score": 1.0,
        "recurrence_containment_score": 1.0,
        "independent_validated": True,
        "sustainability_complete": True,
        "cross_entity_complete": True,
        "commitments_complete": True,
        "second_recurrence_count": 1,
    })
    assert "second_recurrence_requires_escalation" in r["blockers"]
    assert r["ready"] is False


def test_release62_traceability_chain():
    r = evaluate_traceability({
        "reopened_finding": 1, "renewed_remediation": 1, "corrective_action": 1, "retest": 1,
        "independent_revalidation": 1, "sustainability_monitoring": 1, "human_recertification": 1, "reclosure": 1,
    })
    assert r["passed"] is True
