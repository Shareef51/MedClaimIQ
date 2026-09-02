from app.domain.regulatory_examination_renewed_remediation_outcome_validation import renewed_remediation_outcome_validation_contract
from app.evaluation.regulatory_examination_renewed_remediation_outcome_validation import reclosure_readiness

a=renewed_remediation_outcome_validation_contract()["authority"]
assert not a["ai_can_accept_residual_systemic_risk"]
assert not a["ai_can_certify_recovery_effectiveness"]
assert not a["ai_can_reclose_intervention_program"]
r=reclosure_readiness({"all_workstreams_complete":True,"implementation_evidence_complete":True,"independent_recovery_validation_passed":True,"cross_entity_reconciliation_complete":True,"regulatory_commitments_reconciled":True,"unresolved_blockers":0,"sustainability_window_complete":True,"residual_risk_human_accepted":True})
assert r["ready_for_human_executive_reclosure"]
print("Release 81 verification passed")
