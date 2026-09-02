from app.domain.regulatory_examination_reclosed_recovery_surveillance import reclosed_recovery_surveillance_contract
from app.evaluation.regulatory_examination_reclosed_recovery_surveillance import surveillance_score, reopening_readiness

a=reclosed_recovery_surveillance_contract()["authority"]
assert not a["ai_can_reopen_program"] and not a["worker_can_reopen_program"]
s=surveillance_score({"closure_residual_risk_score":20,"current_systemic_risk_score":30,"closure_control_effectiveness":95,"current_control_effectiveness":80,"expected_entity_ids":["US","EU"],"regressed_entity_ids":["EU"]})
assert s["human_investigation_required"]
r=reopening_readiness({"sustainability_breach_confirmed":True,"investigation_complete":True,"independent_reassessment_complete":True,"executive_review_complete":True,"internal_audit_review_complete":True,"prior_certification_compared":True,"renewed_remediation_candidate_prepared":True})
assert r["ready_for_human_enterprise_reopening"]
print("Release 82 verification passed")
