from app.domain.regulatory_reopened_outcome_validation import REOPENED_OUTCOME_AUTHORITY
from app.evaluation.regulatory_reopened_outcome_validation import evaluate_reclosure_readiness, evaluate_traceability

assert REOPENED_OUTCOME_AUTHORITY["ai_can_reclose_finding"] is False
assert REOPENED_OUTCOME_AUTHORITY["human_reclosure_approval_required"] is True
ready = evaluate_reclosure_readiness({"current_effectiveness_score":1,"recurrence_containment_score":1,"independent_validated":True,"sustainability_complete":True,"cross_entity_complete":True,"commitments_complete":True,"second_recurrence_count":0})
assert ready["ready"] is True and ready["score"] == 100
second = evaluate_reclosure_readiness({"current_effectiveness_score":1,"recurrence_containment_score":1,"independent_validated":True,"sustainability_complete":True,"cross_entity_complete":True,"commitments_complete":True,"second_recurrence_count":1})
assert second["ready"] is False
trace = evaluate_traceability({"reopened_finding":1,"renewed_remediation":1,"corrective_action":1,"retest":1,"independent_revalidation":1,"sustainability_monitoring":1,"human_recertification":1,"reclosure":1})
assert trace["passed"] is True
print("Release 62 verification passed")
