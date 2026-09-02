from app.services.regulatory_reopened_outcome_validation import RegulatoryReopenedOutcomeValidationService


def evaluate_reclosure_readiness(case: dict) -> dict:
    blockers = RegulatoryReopenedOutcomeValidationService.readiness_blockers(
        independent_validated=case.get("independent_validated", False),
        sustainability_complete=case.get("sustainability_complete", False),
        cross_entity_complete=case.get("cross_entity_complete", False),
        commitments_complete=case.get("commitments_complete", False),
        second_recurrence_count=case.get("second_recurrence_count", 0),
    )
    score = RegulatoryReopenedOutcomeValidationService.closure_readiness(
        current_effectiveness_score=case.get("current_effectiveness_score", 0),
        containment_score=case.get("recurrence_containment_score", 0),
        independent_validated=case.get("independent_validated", False),
        sustainability_complete=case.get("sustainability_complete", False),
        cross_entity_complete=case.get("cross_entity_complete", False),
        commitments_complete=case.get("commitments_complete", False),
        second_recurrence_count=case.get("second_recurrence_count", 0),
    )
    return {"score": score, "blockers": blockers, "ready": score >= 90 and not blockers, "decision_authority": "human_only"}


def evaluate_traceability(case: dict) -> dict:
    required = ["reopened_finding", "renewed_remediation", "corrective_action", "retest", "independent_revalidation", "sustainability_monitoring", "human_recertification", "reclosure"]
    missing = [k for k in required if not case.get(k)]
    return {"passed": not missing, "missing": missing}
