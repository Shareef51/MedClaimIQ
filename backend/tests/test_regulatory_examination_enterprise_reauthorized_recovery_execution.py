import pytest
from app.domain.regulatory_examination_enterprise_reauthorized_recovery_execution import (
    ENTERPRISE_REAUTHORIZED_RECOVERY_EXECUTION_AUTHORITY,
    enterprise_reauthorized_recovery_execution_contract,
)
from app.evaluation.regulatory_examination_enterprise_reauthorized_recovery_execution import (
    systemic_control_retransformation_status,
    implementation_drift_detection,
    regulatory_commitment_alignment,
    independent_effectiveness_assurance,
    enterprise_wide_control_validation,
    execution_readiness,
)
from app.services.regulatory_examination_enterprise_reauthorized_recovery_execution import RegulatoryExaminationEnterpriseReauthorizedRecoveryExecutionService
from app.workers.regulatory_examination_enterprise_reauthorized_recovery_execution import monitor_enterprise_reauthorized_recovery_execution


def test_authority_boundary_is_non_delegable():
    a = ENTERPRISE_REAUTHORIZED_RECOVERY_EXECUTION_AUTHORITY
    assert a["recommendation_only"] is True
    assert a["release95_enterprise_reauthorization_reference_required"] is True
    assert a["release95_human_reauthorization_confirmation_required"] is True
    assert a["ai_can_approve_control_retransformation"] is False
    assert a["ai_can_accept_residual_systemic_risk"] is False
    assert a["ai_can_certify_recovery_effectiveness"] is False
    assert a["ai_can_close_regulatory_commitments"] is False
    assert a["payment_authority_allowed"] is False
    assert "Release 95 human enterprise recovery reauthorization" in enterprise_reauthorized_recovery_execution_contract()["traceability"]


def test_program_requires_confirmed_release95_human_reauthorization():
    svc = RegulatoryExaminationEnterpriseReauthorizedRecoveryExecutionService(None, "tenant-a")
    base = {
        "actor_role": "recovery_governance",
        "recovery_program_id": "erp-96",
        "enterprise_recovery_reauthorization_version_id": "reauth95-1",
        "release95_investigation_version_id": "inv95-1",
        "release95_investigation_conclusion_version_id": "con95-1",
        "evidence_refs": ["ev-95"],
        "workstreams": [],
    }
    with pytest.raises(ValueError):
        svc.create_program("human-1", {**base, "release95_human_reauthorization_confirmed": False, "release95_reauthorization_decision": "authorize"})
    with pytest.raises(ValueError):
        svc.create_program("human-1", {**base, "release95_human_reauthorization_confirmed": True, "release95_reauthorization_decision": "do_not_authorize"})
    program = svc.create_program("human-1", {**base, "release95_human_reauthorization_confirmed": True, "release95_reauthorization_decision": "authorize"})
    assert program["human_program_intake"] is True
    assert program["automated_program_approval"] is False
    assert program["immutable"] is True


def test_systemic_retransformation_drift_commitments_and_enterprise_validation():
    control = systemic_control_retransformation_status({"controls": [
        {"control_id":"c1","action":"replace","repeated_failure":True,"entity_ids":["e1","e2"],"human_control_retransformation_approval_reference":"ha1","implementation_evidence_refs":["ev1"],"release95_reauthorization_scope_reference":"s1"},
        {"control_id":"c2","action":"redesign","failure_cycle_count":3,"entity_ids":["e1","e2"],"human_control_retransformation_approval_reference":"ha2","implementation_evidence_refs":["ev2"],"release95_reauthorization_scope_reference":"s2"},
    ]})
    assert control["repeated_failure_control_count"] == 2
    assert control["systemic_retransformation_control_count"] == 2
    assert control["control_retransformation_ready"] is True

    drift = implementation_drift_detection({
        "planned_controls":[{"control_id":"c1","design_fingerprint":"v2","entity_ids":["e1","e2"]}],
        "implemented_controls":[{"control_id":"c1","design_fingerprint":"v3","entity_ids":["e1"],"release95_reauthorization_scope_reference":"s1"}],
    })
    assert drift["material_drift"] is True
    assert "c1" in drift["design_drift_control_ids"]
    assert "c1" in drift["entity_scope_drift_control_ids"]

    commitment = regulatory_commitment_alignment({"commitments":[{
        "commitment_id":"r1","mapped_recovery_workstream_id":"w1","mapped_control_ids":["c1"],"evidence_refs":["ev"],"human_commitment_owner_confirmation_reference":"h1","status":"on_track"
    }]})
    assert commitment["alignment_complete"] is True
    assert commitment["automated_commitment_closure_allowed"] is False

    validation = enterprise_wide_control_validation({"control_validations":[
        {"control_id":"c1","status":"effective","entity_ids":["e1","e2"],"evidence_refs":["ev"],"repeated_failure_control":True,"repeated_failure_scope_validated":True}
    ]})
    assert validation["enterprise_validation_passed"] is True
    assert validation["human_effectiveness_certification_required"] is True


def test_independent_assurance_sod_human_approval_and_worker_boundary():
    svc = RegulatoryExaminationEnterpriseReauthorizedRecoveryExecutionService(None, "tenant-a")
    approval = svc.approve_control_retransformation("cro", {
        "actor_role":"chief_risk_officer", "recovery_program_id":"erp-96", "enterprise_recovery_execution_version_id":"exec96", "control_ids":["c1"],
        "release95_reauthorization_scope_references":["s1"], "evidence_refs":["ev1"], "decision":"approve", "rationale":"evidence supports governed retransformation"
    })
    assert approval["human_decision"] and not approval["automated_decision"]

    with pytest.raises(PermissionError):
        svc.independent_assurance("impl-1", {
            "reviewer_role":"internal_auditor", "recovery_program_id":"erp-96", "enterprise_recovery_execution_version_id":"exec96", "implementation_owner_id":"impl-1",
            "tests":[{"result":"pass","independent_reviewer_id":"impl-1","implementation_owner_id":"impl-1","evidence_refs":["ev"],"release95_reauthorization_scope_validated":True,"repeated_failure_scope_validated":True,"cross_entity_effectiveness_validated":True,"entity_ids":["e1","e2"]}], "evidence_refs":["ev"]
        })

    assurance = svc.independent_assurance("aud-1", {
        "reviewer_role":"internal_auditor", "recovery_program_id":"erp-96", "enterprise_recovery_execution_version_id":"exec96", "implementation_owner_id":"impl-1",
        "tests":[{"result":"pass","independent_reviewer_id":"aud-1","implementation_owner_id":"impl-1","evidence_refs":["ev"],"release95_reauthorization_scope_validated":True,"repeated_failure_scope_validated":True,"cross_entity_effectiveness_validated":True,"entity_ids":["e1","e2"]}], "evidence_refs":["ev"]
    })
    assert assurance["evaluation"]["assurance_passed"] is True
    assert assurance["automated_certification"] is False

    readiness = execution_readiness({
        "release95_enterprise_reauthorization_reference_present":True,
        "release95_human_reauthorization_confirmed":True,
        "enterprise_workstreams_defined":True,
        "systemic_control_retransformation_scope_human_approved":True,
        "cross_entity_deployment_sequence_validated":True,
        "regulatory_commitment_alignment_complete":True,
        "critical_path_reviewed":True,
        "implementation_evidence_current":True,
        "systemic_recovery_kpis_baselined":True,
        "independent_effectiveness_assurance_complete":True,
        "enterprise_wide_control_validation_complete":True,
        "material_blockers_resolved_or_human_escalated":True,
    })
    assert readiness["ready_for_human_recovery_outcome_review"] is True
    assert readiness["automated_program_reclosure_allowed"] is False

    worker = monitor_enterprise_reauthorized_recovery_execution({})
    assert worker["monitoring_only"] is True
    assert worker["automated_control_approval"] is False
    assert worker["automated_recovery_certification"] is False
