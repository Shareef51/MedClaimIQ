from app.domain.regulatory_examination_renewed_recovery_execution import RENEWED_RECOVERY_EXECUTION_AUTHORITY,renewed_recovery_execution_contract
from app.evaluation.regulatory_examination_renewed_recovery_execution import control_rehabilitation_status,critical_path_assessment,implementation_drift,recovery_kpis,independent_revalidation,execution_readiness
from app.services.regulatory_examination_renewed_recovery_execution import RegulatoryExaminationRenewedRecoveryExecutionService

def test_release84_non_delegable_authority():
 a=RENEWED_RECOVERY_EXECUTION_AUTHORITY
 assert a["ai_can_approve_control_rehabilitation"] is False and a["ai_can_accept_residual_systemic_risk"] is False and a["ai_can_certify_recovery_effectiveness"] is False and a["worker_can_certify_recovery"] is False

def test_release84_control_rehabilitation_and_critical_path():
 c=control_rehabilitation_status({"controls":[{"control_id":"c1","status":"failed","entity_ids":["US"]},{"control_id":"c2","action":"replace","implementation_evidence_refs":["e1"],"entity_ids":["EU"]}]}); assert c["failed_control_count"]==1 and c["evidence_bound_rehabilitation_count"]==1
 p=critical_path_assessment({"milestones":[{"id":"m1","critical_path":True,"status":"blocked","evidence_refs":[]}]}); assert p["critical_path_at_risk"]

def test_release84_drift_kpis_and_revalidation():
 d=implementation_drift({"planned_controls":[{"control_id":"c1","design_fingerprint":"a"},{"control_id":"c2","design_fingerprint":"b"}],"implemented_controls":[{"control_id":"c1","design_fingerprint":"x"}]}); assert d["material_drift"] and "c2" in d["missing_control_ids"]
 k=recovery_kpis({"metrics":[{"target":90,"actual":95},{"target":80,"actual":70}]}); assert k["breached_metric_count"]==1 and not k["recovery_target_met"]
 r=independent_revalidation({"tests":[{"result":"pass","independent_reviewer_id":"aud1","entity_ids":["US"]}]}); assert r["revalidation_passed"]

def test_release84_human_execution_boundaries_and_readiness():
 svc=RegulatoryExaminationRenewedRecoveryExecutionService(None,"tenant-a")
 try: svc.independent_revalidate("ai",{"reviewer_role":"ai_agent","tests":[]})
 except PermissionError: pass
 else: raise AssertionError("AI cannot independently certify recovery")
 try: svc.create_program("ai",{"actor_role":"ai_agent","authorization_version_id":"auth-1","program_summary":"x"})
 except PermissionError: pass
 else: raise AssertionError("AI cannot approve renewed recovery program")
 ready=execution_readiness({"human_authorization_reference_present":True,"program_workstreams_defined":True,"control_rehabilitation_scope_approved":True,"commitment_mapping_complete":True,"critical_path_reviewed":True,"execution_evidence_current":True,"independent_revalidation_complete":True}); assert ready["ready_for_human_outcome_review"] and ready["execution_readiness_score"]==100
 assert "independent revalidation" in renewed_recovery_execution_contract()["traceability"]
