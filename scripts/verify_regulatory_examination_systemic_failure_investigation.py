from app.domain.regulatory_examination_systemic_failure_investigation import SYSTEMIC_FAILURE_INVESTIGATION_AUTHORITY
from app.evaluation.regulatory_examination_systemic_failure_investigation import remediation_reauthorization_readiness

a=SYSTEMIC_FAILURE_INVESTIGATION_AUTHORITY
assert not a["ai_can_authorize_remediation"] and not a["ai_can_accept_residual_systemic_risk"] and not a["ai_can_certify_controls"]
r=remediation_reauthorization_readiness({"evidence_reconstructed":True,"root_cause_human_confirmed":True,"cross_entity_scope_validated":True,"independent_challenge_complete":True,"regulator_follow_up_assessed":True,"renewed_strategy_documented":True})
assert r["ready_for_human_authorization"] and not r["automated_authorization_allowed"]
print("Release 79 systemic-failure investigation governance verification passed")
