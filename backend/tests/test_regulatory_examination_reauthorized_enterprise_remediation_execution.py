import pytest
from app.domain.regulatory_examination_reauthorized_enterprise_remediation_execution import REAUTHORIZED_ENTERPRISE_REMEDIATION_EXECUTION_AUTHORITY, reauthorized_enterprise_remediation_execution_contract
from app.evaluation.regulatory_examination_reauthorized_enterprise_remediation_execution import root_cause_treatment_mapping, systemic_control_retransformation_status, implementation_drift_detection, regulatory_commitment_alignment, independent_recovery_effectiveness_assurance, enterprise_wide_control_validation, execution_readiness
from app.services.regulatory_examination_reauthorized_enterprise_remediation_execution import RegulatoryExaminationReauthorizedEnterpriseRemediationExecutionService
from app.workers.regulatory_examination_reauthorized_enterprise_remediation_execution import monitor_reauthorized_enterprise_remediation_execution

def test_release100_authority_boundary_non_delegable():
    a=REAUTHORIZED_ENTERPRISE_REMEDIATION_EXECUTION_AUTHORITY
    assert a["release99_enterprise_remediation_reauthorization_reference_required"]
    assert a["release99_human_reauthorization_confirmation_required"]
    assert not a["ai_can_approve_remediation_execution"] and not a["ai_can_approve_control_retransformation"]
    assert not a["ai_can_accept_residual_systemic_risk"] and not a["ai_can_certify_recovery_effectiveness"]
    assert not a["worker_can_approve_remediation_execution"] and not a["payment_authority_allowed"]
    assert "Release 99 human enterprise remediation reauthorization" in reauthorized_enterprise_remediation_execution_contract()["traceability"]

def test_release100_release99_provenance_and_root_cause_treatment_mapping():
    svc=RegulatoryExaminationReauthorizedEnterpriseRemediationExecutionService(None,"tenant-a")
    p={"actor_role":"remediation_governance","remediation_program_id":"rp100","enterprise_remediation_reauthorization_version_id":"ra99","release99_investigation_version_id":"inv99","release99_investigation_conclusion_version_id":"con99","release99_root_cause_confirmation_version_id":"rc99","release99_systemic_failure_classification_version_id":"sf99","release99_strategy_candidate_version_id":"st99","release99_independent_challenge_version_id":"ch99","release99_human_reauthorization_confirmed":True,"release99_reauthorization_decision":"authorize","evidence_refs":["ev99"],"workstreams":[]}
    created=svc.create_program("human-1",p); assert created["human_program_intake"] and not created["automated_program_approval"]
    bad=dict(p); bad["enterprise_remediation_reauthorization_version_id"]=""
    with pytest.raises(ValueError): svc.create_program("human-1",bad)
    mapping=root_cause_treatment_mapping({"root_cause_treatments":[{"root_cause_id":"r1","root_cause_class":"persistent","remediation_workstream_id":"w1","control_ids":["c1"],"entity_ids":["e1","e2"],"evidence_refs":["ev"],"release99_reauthorization_scope_reference":"s99","human_treatment_owner_confirmation_reference":"h1"},{"root_cause_id":"r2","root_cause_class":"emergent","remediation_workstream_id":"w2","control_ids":["c2"],"entity_ids":["e3"],"evidence_refs":["ev2"],"release99_reauthorization_scope_reference":"s99","human_treatment_owner_confirmation_reference":"h2"}]})
    assert mapping["treatment_mapping_complete"] and mapping["persistent_treatment_count"]==1 and mapping["emergent_treatment_count"]==1

def test_release100_control_drift_commitments_and_enterprise_validation():
    c=systemic_control_retransformation_status({"controls":[{"control_id":"c1","action":"replace","repeated_failure":True,"entity_ids":["e1","e2"],"human_control_retransformation_approval_reference":"ha","implementation_evidence_refs":["ev"],"release99_reauthorization_scope_reference":"s99","root_cause_treatment_reference":"rt1"}]})
    assert c["control_retransformation_ready"] and c["repeated_failure_control_count"]==1
    d=implementation_drift_detection({"planned_controls":[{"control_id":"c1","design_fingerprint":"v2","entity_ids":["e1","e2"]}],"implemented_controls":[{"control_id":"c1","design_fingerprint":"v3","entity_ids":["e1"],"release99_reauthorization_scope_reference":"s99","root_cause_treatment_reference":"rt1"}]})
    assert d["material_drift"] and "c1" in d["design_drift_control_ids"]
    ca=regulatory_commitment_alignment({"commitments":[{"commitment_id":"cm1","mapped_remediation_workstream_id":"w1","mapped_control_ids":["c1"],"evidence_refs":["ev"],"human_commitment_owner_confirmation_reference":"h","status":"on_track"}]})
    assert ca["alignment_complete"] and not ca["automated_commitment_closure_allowed"]
    v=enterprise_wide_control_validation({"control_validations":[{"control_id":"c1","status":"effective","entity_ids":["e1","e2"],"evidence_refs":["ev"],"root_cause_treatment_validated":True,"repeated_failure_control":True,"repeated_failure_scope_validated":True}]})
    assert v["enterprise_validation_passed"] and v["human_effectiveness_certification_required"]

def test_release100_independent_assurance_sod_readiness_and_worker_boundary():
    svc=RegulatoryExaminationReauthorizedEnterpriseRemediationExecutionService(None,"tenant-a")
    approval=svc.approve_control_retransformation("cro",{"actor_role":"chief_risk_officer","remediation_program_id":"rp100","enterprise_remediation_execution_version_id":"exec100","control_ids":["c1"],"release99_reauthorization_scope_references":["s99"],"root_cause_treatment_references":["rt1"],"evidence_refs":["ev"],"decision":"approve","rationale":"human governed approval"})
    assert approval["human_decision"] and not approval["automated_decision"]
    with pytest.raises(PermissionError): svc.independent_assurance("impl-1",{"reviewer_role":"internal_auditor","remediation_program_id":"rp100","enterprise_remediation_execution_version_id":"exec100","implementation_owner_id":"impl-1","tests":[{"result":"pass","independent_reviewer_id":"impl-1","implementation_owner_id":"impl-1","evidence_refs":["ev"],"release99_reauthorization_scope_validated":True,"systemic_root_cause_treatment_validated":True,"repeated_failure_scope_validated":True,"cross_entity_effectiveness_validated":True,"entity_ids":["e1","e2"]}],"evidence_refs":["ev"]})
    assurance=svc.independent_assurance("aud-1",{"reviewer_role":"internal_auditor","remediation_program_id":"rp100","enterprise_remediation_execution_version_id":"exec100","implementation_owner_id":"impl-1","tests":[{"result":"pass","independent_reviewer_id":"aud-1","implementation_owner_id":"impl-1","evidence_refs":["ev"],"release99_reauthorization_scope_validated":True,"systemic_root_cause_treatment_validated":True,"repeated_failure_scope_validated":True,"cross_entity_effectiveness_validated":True,"entity_ids":["e1","e2"]}],"evidence_refs":["ev"]})
    assert assurance["evaluation"]["assurance_passed"] and not assurance["automated_certification"]
    ready=execution_readiness({k:True for k in ["release99_enterprise_remediation_reauthorization_reference_present","release99_human_reauthorization_confirmed","enterprise_remediation_workstreams_defined","systemic_root_cause_treatments_human_confirmed","systemic_control_retransformation_scope_human_approved","cross_entity_deployment_sequence_validated","regulatory_commitment_alignment_complete","critical_path_reviewed","implementation_evidence_current","systemic_recovery_kpis_baselined","independent_recovery_effectiveness_assurance_complete","enterprise_wide_control_validation_complete","material_blockers_resolved_or_human_escalated","executive_supervisory_review_complete"]})
    assert ready["ready_for_human_enterprise_recovery_outcome_review"] and not ready["automated_program_reclosure_allowed"]
    w=monitor_reauthorized_enterprise_remediation_execution({}); assert w["monitoring_only"] and not w["automated_control_approval"] and not w["automated_recovery_certification"]
