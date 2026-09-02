from app.domain.regulatory_examination_reopened_commitment_reclosure import REOPENED_COMMITMENT_RECLOSURE_AUTHORITY
from app.evaluation.regulatory_examination_reopened_commitment_reclosure import reclosure_readiness, second_recurrence_assessment

def main():
    assert REOPENED_COMMITMENT_RECLOSURE_AUTHORITY["ai_can_reclose_commitment"] is False
    ready=reclosure_readiness({"renewed_plan_approved":True,"all_milestones_complete":True,"cross_entity_propagation_complete":True,"regulator_follow_up_reconciled":True,"independent_retest_passed":True,"independent_revalidation_complete":True,"evidence_sufficient":True,"sustainability_reset_ready":True,"second_recurrence_detected":False})
    assert ready["score"]==100 and ready["ready"] is True
    assert second_recurrence_assessment([{"event_type":"recurrence"},{"event_type":"control_failure"}])["executive_escalation_required"] is True
    print("Release 71 verification passed")
if __name__=="__main__": main()
