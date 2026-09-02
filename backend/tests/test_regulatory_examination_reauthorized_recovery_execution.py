from app.domain.regulatory_examination_reauthorized_recovery_execution import REAUTHORIZED_RECOVERY_EXECUTION_AUTHORITY,reauthorized_recovery_execution_contract
from app.evaluation.regulatory_examination_reauthorized_recovery_execution import control_rerehabilitation_status,deployment_sequence_assessment,implementation_drift,independent_recovery_assurance,execution_readiness
from app.services.regulatory_examination_reauthorized_recovery_execution import RegulatoryExaminationReauthorizedRecoveryExecutionService

def test_release88_non_delegable_authority():
    a=REAUTHORIZED_RECOVERY_EXECUTION_AUTHORITY
    assert a["human_reauthorization_reference_required"]
    assert not a["ai_can_approve_control_rerehabilitation"] and not a["ai_can_accept_residual_systemic_risk"] and not a["ai_can_certify_recovery_effectiveness"]
    assert not a["worker_can_approve_control_rerehabilitation"] and not a["worker_can_certify_recovery"]

def test_release88_rerehabilitation_sequence_and_drift():
    r=control_rerehabilitation_status({"controls":[{"control_id":"c1","failure_count":3,"action":"replace","entity_ids":["US"],"implementation_evidence_refs":["e1"],"human_approval_reference":"ha1"},{"control_id":"c2","repeated_failure":True,"action":"re-rehabilitate","entity_ids":["EU"],"implementation_evidence_refs":["e2"],"human_approval_reference":"ha2"}]})
    assert r["repeated_failure_control_count"]==2 and r["evidence_bound_control_count"]==2 and r["missing_human_approval_count"]==0
    s=deployment_sequence_assessment({"deployment_steps":[{"sequence":1,"entity_ids":["US"],"dependencies_satisfied":True},{"sequence":2,"entity_ids":["EU"],"dependencies_satisfied":True}]})
    assert not s["sequence_at_risk"]
    d=implementation_drift({"planned_controls":[{"control_id":"c1","design_fingerprint":"v2"}],"implemented_controls":[{"control_id":"c1","design_fingerprint":"v2","human_approval_reference":"ha1"}]})
    assert not d["material_drift"]

def test_release88_independent_assurance_and_readiness():
    a=independent_recovery_assurance({"tests":[{"result":"pass","independent_reviewer_id":"ia1","repeated_failure_scope_validated":True,"entity_ids":["US"]},{"result":"effective","independent_reviewer_id":"ia2","repeated_failure_scope_validated":True,"entity_ids":["EU"]}]})
    assert a["assurance_passed"] and not a["automated_certification_allowed"]
    ready=execution_readiness({"human_reauthorization_reference_present":True,"reauthorized_workstreams_defined":True,"control_rerehabilitation_scope_human_approved":True,"cross_entity_sequence_validated":True,"regulatory_commitment_alignment_complete":True,"critical_path_reviewed":True,"execution_evidence_current":True,"independent_recovery_assurance_complete":True})
    assert ready["ready_for_human_outcome_review"] and ready["execution_readiness_score"]==100.0 and not ready["automated_certification_allowed"]

def test_release88_human_reauthorization_prerequisite_and_review_boundary():
    svc=RegulatoryExaminationReauthorizedRecoveryExecutionService(None,"tenant-a")
    try: svc.create_program("ai",{"actor_role":"ai_agent","recovery_program_id":"rp1","remediation_reauthorization_version_id":"ra1"})
    except PermissionError: pass
    else: raise AssertionError("AI cannot create authoritative reauthorized execution program")
    try: svc.create_program("cro",{"actor_role":"chief_risk_officer","recovery_program_id":"rp1"})
    except ValueError: pass
    else: raise AssertionError("human remediation reauthorization reference is mandatory")
    program=svc.create_program("cro",{"actor_role":"chief_risk_officer","recovery_program_id":"rp1","remediation_reauthorization_version_id":"ra1"})
    assert program["human_reauthorization_reference_required"] and not program["automated_program_approval"]
    review=svc.executive_review("cro",{"actor_role":"chief_risk_officer","decision":"continue","rationale":"continue controlled recovery"})
    assert review["human_decision"] and not review["automated_decision"]
    assert "human remediation reauthorization" in reauthorized_recovery_execution_contract()["traceability"]
