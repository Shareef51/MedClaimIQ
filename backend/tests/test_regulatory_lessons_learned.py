from app.domain.regulatory_lessons_learned import LESSONS_LEARNED_AUTHORITY
from app.evaluation.regulatory_lessons_learned import evaluate_effectiveness_benchmark, evaluate_improvement_priority, evaluate_traceability


def test_release63_non_delegable_control_change_authority():
    assert LESSONS_LEARNED_AUTHORITY["ai_can_approve_control_change"] is False
    assert LESSONS_LEARNED_AUTHORITY["ai_can_modify_policy_or_procedure"] is False
    assert LESSONS_LEARNED_AUTHORITY["ai_can_certify_control_effectiveness"] is False
    assert LESSONS_LEARNED_AUTHORITY["worker_can_collect_or_move_money"] is False


def test_release63_effectiveness_benchmark_is_bounded_and_evidence_grounded():
    r = evaluate_effectiveness_benchmark({"outcome_success_rate": .9, "retest_pass_rate": .8, "recurrence_free_rate": 1, "sustainability_score": .9, "evidence_refs": [{"id": "ev1"}]})
    assert 0 <= r["score"] <= 1
    assert r["evidence_grounded"] is True
    assert r["decision_authority"] == "human_only"


def test_release63_improvement_priority_is_recommendation_only():
    r = evaluate_improvement_priority({"recurrence_risk": 1, "control_criticality": 1, "cross_entity_exposure": .5, "regulator_relevance": 1})
    assert r["priority_score"] == 90.0
    assert r["recommendation_only"] is True


def test_release63_traceability_chain():
    r = evaluate_traceability({"remediation_outcome": 1, "lesson": 1, "control_improvement": 1, "human_approval": 1, "implementation": 1, "future_examination_evidence": 1})
    assert r["passed"] is True
