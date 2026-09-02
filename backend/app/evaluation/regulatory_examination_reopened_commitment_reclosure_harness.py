from app.domain.regulatory_examination_reopened_commitment_reclosure import REOPENED_COMMITMENT_RECLOSURE_AUTHORITY
from app.evaluation.regulatory_examination_reopened_commitment_reclosure import reclosure_readiness, second_recurrence_assessment

def run_harness()->dict:
    assert REOPENED_COMMITMENT_RECLOSURE_AUTHORITY["ai_can_reclose_commitment"] is False
    ready=reclosure_readiness({"renewed_plan_approved":True,"all_milestones_complete":True,"cross_entity_propagation_complete":True,"regulator_follow_up_reconciled":True,"independent_retest_passed":True,"independent_revalidation_complete":True,"evidence_sufficient":True,"sustainability_reset_ready":True,"second_recurrence_detected":False})
    recurring=second_recurrence_assessment([{"event_type":"recurrence"},{"event_type":"control_failure"}])
    return {"ready_score":ready["score"],"second_recurrence":recurring["second_recurrence"],"passed":ready["ready"] and recurring["executive_escalation_required"]}
