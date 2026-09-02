from app.services.regulatory_lessons_learned import RegulatoryLessonsLearnedService


def evaluate_effectiveness_benchmark(case: dict) -> dict:
    score = RegulatoryLessonsLearnedService.effectiveness_benchmark(
        outcome_success_rate=case.get("outcome_success_rate", 0), retest_pass_rate=case.get("retest_pass_rate", 0),
        recurrence_free_rate=case.get("recurrence_free_rate", 0), sustainability_score=case.get("sustainability_score", 0))
    return {"score": score, "evidence_grounded": bool(case.get("evidence_refs")), "decision_authority": "human_only"}


def evaluate_improvement_priority(case: dict) -> dict:
    score = RegulatoryLessonsLearnedService.improvement_priority(
        recurrence_risk=case.get("recurrence_risk", 0), control_criticality=case.get("control_criticality", 0),
        cross_entity_exposure=case.get("cross_entity_exposure", 0), regulator_relevance=case.get("regulator_relevance", 0))
    return {"priority_score": score, "recommendation_only": True}


def evaluate_traceability(case: dict) -> dict:
    required = ["remediation_outcome", "lesson", "control_improvement", "human_approval", "implementation", "future_examination_evidence"]
    missing = [k for k in required if not case.get(k)]
    return {"passed": not missing, "missing": missing}
