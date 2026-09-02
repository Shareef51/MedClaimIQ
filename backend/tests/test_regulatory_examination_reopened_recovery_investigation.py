from app.domain.regulatory_examination_reopened_recovery_investigation import REOPENED_RECOVERY_INVESTIGATION_AUTHORITY,reopened_recovery_investigation_contract
from app.evaluation.regulatory_examination_reopened_recovery_investigation import reconstruct_systemic_decay,validate_prior_recovery_assumptions,reassess_decay_root_causes,analyze_cross_entity_control_gaps,authorization_readiness
from app.services.regulatory_examination_reopened_recovery_investigation import RegulatoryExaminationReopenedRecoveryInvestigationService
def test_release83_non_delegable_authority():
 a=REOPENED_RECOVERY_INVESTIGATION_AUTHORITY
 assert a["ai_can_authorize_renewed_remediation"] is False and a["ai_can_accept_residual_systemic_risk"] is False and a["ai_can_certify_recovery_effectiveness"] is False and a["worker_can_authorize_renewed_remediation"] is False
def test_release83_decay_assumption_and_root_cause_reconstruction():
 d=reconstruct_systemic_decay({"decay_cycles":[{"cycle_id":"c1","root_cause_id":"r1","entity_ids":["US"],"evidence_refs":["e1"]},{"cycle_id":"c2","root_cause_id":"r1","entity_ids":["EU"],"evidence_refs":["e2"]}]}); assert d["systemic_decay_reconstructed"] and d["affected_entity_count"]==2
 a=validate_prior_recovery_assumptions({"assumptions":[{"status":"breached"},{"status":"valid"}]}); assert a["prior_recovery_assumptions_at_risk"]
 r=reassess_decay_root_causes({"prior_root_cause_ids":["r1"],"current_root_cause_ids":["r1","r2"],"recovery_control_failed":True}); assert r["persistent_root_cause_pattern"] and "r2" in r["new_root_cause_ids"]
def test_release83_control_gaps_and_authorization_readiness():
 g=analyze_cross_entity_control_gaps({"control_gaps":[{"severity":"critical","entity_ids":["US"]},{"recovery_control_failed":True,"entity_ids":["EU"]}]}); assert g["enterprise_control_gap"]
 ready=authorization_readiness({"systemic_decay_reconstructed":True,"root_cause_human_confirmed":True,"cross_entity_gap_scope_validated":True,"regulator_follow_up_assessed":True,"commitment_alignment_complete":True,"independent_challenge_complete":True,"renewed_strategy_documented":True}); assert ready["ready_for_human_authorization"] and ready["authorization_readiness_score"]==100
def test_release83_human_authorization_boundaries():
 svc=RegulatoryExaminationReopenedRecoveryInvestigationService(None,"tenant-a")
 try: svc.independent_challenge("ai",{"reviewer_role":"ai_agent","decision":"agree","rationale":"x"})
 except PermissionError: pass
 else: raise AssertionError("AI cannot independently challenge")
 readiness={"systemic_decay_reconstructed":True,"root_cause_human_confirmed":True,"cross_entity_gap_scope_validated":True,"regulator_follow_up_assessed":True,"commitment_alignment_complete":True,"independent_challenge_complete":True,"renewed_strategy_documented":True}
 try: svc.authorize("ai",{"actor_role":"ai_agent","decision":"authorize","rationale":"x","readiness":readiness})
 except PermissionError: pass
 else: raise AssertionError("AI cannot authorize renewed remediation")
 result=svc.authorize("cro",{"actor_role":"chief_risk_officer","decision":"authorize","rationale":"human approval","readiness":readiness,"evidence_refs":["e1"]}); assert result["human_authorization"] and not result["automated_authorization"]
 assert "governed recovery execution" in reopened_recovery_investigation_contract()["traceability"]
