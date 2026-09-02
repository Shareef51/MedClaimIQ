from app.domain.regulatory_examination_supervisory_reauthorized_recovery_execution import (
    SUPERVISORY_REAUTHORIZED_RECOVERY_EXECUTION_AUTHORITY,
    supervisory_reauthorized_recovery_execution_contract,
)
from app.evaluation.regulatory_examination_supervisory_reauthorized_recovery_execution import (
    control_retransformation_status,
    deployment_sequence_assessment,
    implementation_drift,
    independent_recovery_assurance,
    execution_readiness,
)
from app.services.regulatory_examination_supervisory_reauthorized_recovery_execution import RegulatoryExaminationSupervisoryReauthorizedRecoveryExecutionService


def test_release92_non_delegable_authority():
    a = SUPERVISORY_REAUTHORIZED_RECOVERY_EXECUTION_AUTHORITY
    assert a["release91_supervisory_reauthorization_reference_required"]
    assert a["independent_recovery_assurance_required"]
    assert not a["ai_can_approve_control_retransformation"]
    assert not a["ai_can_accept_residual_systemic_risk"]
    assert not a["ai_can_certify_recovery_effectiveness"]
    assert not a["worker_can_approve_control_retransformation"]
    assert not a["worker_can_certify_recovery"]


def test_release92_retransformation_sequence_and_drift():
    controls = control_retransformation_status({"controls": [
        {"control_id": "c1", "failure_count": 4, "action": "replace", "entity_ids": ["US"], "implementation_evidence_refs": ["e1"], "human_approval_reference": "ha1", "release91_reauthorization_scope_reference": "ra91"},
        {"control_id": "c2", "repeated_failure": True, "action": "retransform", "entity_ids": ["EU"], "implementation_evidence_refs": ["e2"], "human_approval_reference": "ha2", "release91_reauthorization_scope_reference": "ra91"},
    ]})
    assert controls["repeated_failure_control_count"] == 2
    assert controls["evidence_bound_control_count"] == 2
    assert controls["missing_human_approval_count"] == 0
    assert controls["missing_release91_scope_reference_count"] == 0
    seq = deployment_sequence_assessment({"deployment_steps": [
        {"sequence": 1, "entity_ids": ["US"], "dependencies_satisfied": True, "human_sequence_approval_reference": "s1"},
        {"sequence": 2, "entity_ids": ["EU"], "dependencies_satisfied": True, "human_sequence_approval_reference": "s2"},
    ]})
    assert not seq["sequence_at_risk"]
    drift = implementation_drift({
        "planned_controls": [{"control_id": "c1", "design_fingerprint": "v4"}],
        "implemented_controls": [{"control_id": "c1", "design_fingerprint": "v4", "human_approval_reference": "ha1", "release91_reauthorization_scope_reference": "ra91"}],
    })
    assert not drift["material_drift"] and not drift["human_review_required"]


def test_release92_independent_assurance_and_readiness():
    assurance = independent_recovery_assurance({"tests": [
        {"result": "pass", "independent_reviewer_id": "ia1", "release91_reauthorization_scope_validated": True, "cross_entity_effectiveness_validated": True, "repeated_failure_scope_validated": True, "entity_ids": ["US"]},
        {"result": "effective", "independent_reviewer_id": "ia2", "release91_reauthorization_scope_validated": True, "cross_entity_effectiveness_validated": True, "repeated_failure_scope_validated": True, "entity_ids": ["EU"]},
    ]})
    assert assurance["assurance_passed"] and not assurance["automated_certification_allowed"]
    ready = execution_readiness({
        "release91_supervisory_reauthorization_reference_present": True,
        "supervisory_workstreams_defined": True,
        "control_retransformation_scope_human_approved": True,
        "cross_entity_sequence_validated": True,
        "regulatory_commitment_alignment_complete": True,
        "critical_path_reviewed": True,
        "execution_evidence_current": True,
        "recovery_kpis_baselined": True,
        "independent_recovery_assurance_complete": True,
    })
    assert ready["ready_for_human_outcome_review"]
    assert ready["execution_readiness_score"] == 100.0
    assert not ready["automated_certification_allowed"]


def test_release92_release91_human_reauthorization_prerequisite_and_human_review():
    svc = RegulatoryExaminationSupervisoryReauthorizedRecoveryExecutionService(None, "tenant-a")
    try:
        svc.create_program("ai", {"actor_role": "ai_agent", "recovery_program_id": "rp1", "supervisory_recovery_reauthorization_version_id": "ra91", "release91_investigation_version_id": "inv91"})
    except PermissionError:
        pass
    else:
        raise AssertionError("AI cannot create authoritative supervisory reauthorized recovery execution program")
    try:
        svc.create_program("cro", {"actor_role": "chief_risk_officer", "recovery_program_id": "rp1", "release91_investigation_version_id": "inv91"})
    except ValueError:
        pass
    else:
        raise AssertionError("Release 91 supervisory recovery reauthorization reference is mandatory")
    program = svc.create_program("cro", {"actor_role": "chief_risk_officer", "recovery_program_id": "rp1", "supervisory_recovery_reauthorization_version_id": "ra91", "release91_investigation_version_id": "inv91"})
    assert program["release91_human_reauthorization_reference_required"] and not program["automated_program_approval"]
    checkpoint = svc.create_checkpoint("cro", {"actor_role": "chief_risk_officer", "recovery_program_id": "rp1", "supervisory_recovery_execution_version_id": program["supervisory_reauthorized_recovery_execution_version_id"], "checkpoint_type": "control-rollout", "status": "complete", "evidence_refs": ["ev1"]})
    assert checkpoint["human_checkpoint"] and not checkpoint["automated_completion_certification"]
    review = svc.executive_review("cro", {"actor_role": "chief_risk_officer", "recovery_program_id": "rp1", "supervisory_recovery_execution_version_id": program["supervisory_reauthorized_recovery_execution_version_id"], "decision": "continue", "rationale": "continue governed recovery"})
    assert review["human_decision"] and not review["automated_decision"]
    assert "Release 91 human supervisory recovery reauthorization" in supervisory_reauthorized_recovery_execution_contract()["traceability"]
