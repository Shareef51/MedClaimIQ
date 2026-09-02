from app.domain.regulatory_examination_reopened_enterprise_intervention import REOPENED_ENTERPRISE_INTERVENTION_AUTHORITY
from app.evaluation.regulatory_examination_reopened_enterprise_intervention import reclosure_readiness, second_systemic_recurrence

a=REOPENED_ENTERPRISE_INTERVENTION_AUTHORITY
assert not a["ai_can_accept_residual_systemic_risk"] and not a["ai_can_reclose_intervention_program"]
ready=reclosure_readiness({"renewed_plan_human_approved":True,"all_milestones_complete":True,"cross_entity_remediation_complete":True,"regulator_commitments_reconciled":True,"evidence_complete":True,"independent_revalidation_passed":True,"sustainability_reset_complete":True,"human_residual_risk_reassessed":True,"second_systemic_recurrence_detected":False})
assert ready["reclosure_readiness_score"]==100
assert second_systemic_recurrence([{"event_type":"systemic_recurrence"},{"event_type":"program_reopen"}])["second_systemic_recurrence"]
print("Release 77 verification passed")
