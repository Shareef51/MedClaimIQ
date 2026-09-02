from app.domain.regulatory_examination_reopened_supervisory_recovery_investigation import (
    REOPENED_SUPERVISORY_RECOVERY_INVESTIGATION_AUTHORITY,
    reopened_supervisory_recovery_investigation_contract,
)
from app.evaluation.regulatory_examination_reopened_supervisory_recovery_investigation import (
    reconstruct_multi_cycle_supervisory_evidence,
    reconstruct_persistent_emergent_root_causes,
    validate_prior_recertification_reclosure_assumptions,
    analyze_repeated_control_retransformation_failures,
    classify_enterprise_systemic_failure,
    enterprise_recovery_reauthorization_readiness,
)
from app.services.regulatory_examination_reopened_supervisory_recovery_investigation import RegulatoryExaminationReopenedSupervisoryRecoveryInvestigationService


def test_release95_non_delegable_authority_and_release94_provenance():
    a=REOPENED_SUPERVISORY_RECOVERY_INVESTIGATION_AUTHORITY
    assert a["release94_human_reopening_reference_required"]
    assert a["human_root_cause_confirmation_required"]
    assert a["human_systemic_failure_classification_confirmation_required"]
    assert not a["ai_can_authorize_recovery_remediation"]
    assert not a["ai_can_confirm_root_cause"]
    assert not a["ai_can_confirm_systemic_failure_classification"]
    assert not a["worker_can_authorize_recovery_remediation"]


def test_release95_multi_cycle_evidence_and_persistent_emergent_root_causes():
    evidence=reconstruct_multi_cycle_supervisory_evidence({"cycles":[
        {"cycle_id":"c1","sequence":1,"status":"failed","evidence_refs":["e1"],"reclosure_version_id":"r1","independent_assurance_version_id":"a1"},
        {"cycle_id":"c2","sequence":2,"status":"recurred","evidence_refs":["e2"],"reopening_version_id":"o2","independent_assurance_version_id":"a2"},
        {"cycle_id":"c3","sequence":3,"status":"failed","evidence_refs":["e3"],"reclosure_version_id":"r3"},
    ]})
    assert evidence["full_multi_cycle_evidence_reconstructed"] and evidence["repeated_supervisory_failure_pattern"]
    roots=reconstruct_persistent_emergent_root_causes({
        "prior_root_cause_ids":["r1"],"historical_root_cause_ids":["r0","r1"],"current_root_cause_ids":["r1","r2"],
        "repeated_control_retransformation_failure_count":3,"systemic_risk_rebound_confirmed":True,"cross_entity_recurrence_confirmed":True,
    })
    assert roots["persistent_root_cause_ids"] == ["r1"]
    assert roots["emergent_root_cause_ids"] == ["r2"]
    assert roots["persistent_systemic_root_cause_candidate"]


def test_release95_assumptions_control_failure_classification_and_readiness():
    assumptions=validate_prior_recertification_reclosure_assumptions({"assumptions":[
        {"assumption_id":"a1","current_status":"contradicted"},{"assumption_id":"a2","current_status":"confirmed"}
    ]})
    assert assumptions["prior_executive_recertification_reclosure_assumptions_at_risk"]
    controls=analyze_repeated_control_retransformation_failures({"controls":[
        {"control_id":"ctrl1","status":"failed","failure_cycle_count":3,"entity_ids":["US","EU"],"root_cause_ids":["r1"]},
        {"control_id":"ctrl2","retransformation_effective":False,"failure_cycle_count":2,"entity_ids":["APAC"]},
    ]})
    assert controls["enterprise_retransformation_failure_candidate"] and len(controls["repeated_failure_control_ids"]) == 2
    classification=classify_enterprise_systemic_failure({"multi_cycle_root_cause_risk_score":90,"failed_control_retransformation_count":4,"affected_entity_count":3,"systemic_risk_rebound_percent":70,"repeated_failure_cycle_count":4,"material_regulator_followup_count":2})
    assert classification["enterprise_systemic_failure_candidate"] and classification["human_classification_confirmation_required"]
    ready=enterprise_recovery_reauthorization_readiness({
        "release94_human_reopening_verified":True,"formal_investigation_complete":True,"full_multi_cycle_evidence_reconstructed":True,
        "prior_recertification_reclosure_assumptions_validated":True,"persistent_emergent_root_causes_human_confirmed":True,
        "repeated_control_retransformation_failure_assessed":True,"cross_entity_causal_propagation_human_validated":True,
        "regulator_followup_impact_human_interpreted":True,"enterprise_systemic_failure_classification_human_confirmed":True,
        "renewed_recovery_strategy_documented":True,"independent_internal_audit_challenge_complete":True,
        "executive_review_complete":True,"evidence_bound_reauthorization_package_complete":True,
    })
    assert ready["ready_for_human_enterprise_recovery_reauthorization"] and ready["enterprise_recovery_reauthorization_readiness_score"] == 100.0
    assert not ready["automated_reauthorization_allowed"]


def test_release95_release94_reopening_human_root_cause_and_executive_reauthorization_boundary():
    svc=RegulatoryExaminationReopenedSupervisoryRecoveryInvestigationService(None,"tenant-a")
    try:
        svc.create_investigation("ai",{"actor_role":"ai_agent","recovery_program_id":"rp1","release94_enterprise_reopening_version_id":"op94","summary":"x","surveillance_version_refs":["s1"],"evidence_refs":["e1"]})
    except PermissionError: pass
    else: raise AssertionError("AI cannot open authoritative reopened supervisory recovery investigation")
    try:
        svc.create_investigation("ia",{"actor_role":"internal_auditor","recovery_program_id":"rp1","release94_enterprise_reopening_version_id":"","summary":"x","surveillance_version_refs":["s1"],"evidence_refs":["e1"]})
    except ValueError: pass
    else: raise AssertionError("Release 94 human reopening reference is mandatory")
    rc=svc.confirm_root_causes("ia",{"actor_role":"internal_auditor","recovery_program_id":"rp1","investigation_version_id":"inv95","root_cause_analysis_version_id":"rca95","confirmed_persistent_root_cause_ids":["r1"],"confirmed_emergent_root_cause_ids":["r2"],"conclusion":"confirmed","evidence_refs":["e1"]})
    assert rc["human_confirmation"] and not rc["automated_confirmation"]
    full={
        "release94_human_reopening_verified":True,"formal_investigation_complete":True,"full_multi_cycle_evidence_reconstructed":True,
        "prior_recertification_reclosure_assumptions_validated":True,"persistent_emergent_root_causes_human_confirmed":True,
        "repeated_control_retransformation_failure_assessed":True,"cross_entity_causal_propagation_human_validated":True,
        "regulator_followup_impact_human_interpreted":True,"enterprise_systemic_failure_classification_human_confirmed":True,
        "renewed_recovery_strategy_documented":True,"independent_internal_audit_challenge_complete":True,
        "executive_review_complete":True,"evidence_bound_reauthorization_package_complete":True,
    }
    payload={"actor_role":"ai_agent","decision":"authorize","rationale":"x","recovery_program_id":"rp1","release94_enterprise_reopening_version_id":"op94","investigation_version_id":"inv95","investigation_conclusion_version_id":"con95","root_cause_confirmation_version_id":"rc95","systemic_failure_classification_version_id":"sf95","strategy_candidate_version_id":"st95","independent_challenge_version_id":"ch95","evidence_refs":["e1"],"readiness":full}
    try: svc.authorize_recovery("ai",payload)
    except PermissionError: pass
    else: raise AssertionError("AI cannot reauthorize enterprise recovery remediation")
    payload["actor_role"]="chief_risk_officer"
    result=svc.authorize_recovery("cro",payload)
    assert result["human_reauthorization"] and not result["automated_reauthorization"]
    assert "human enterprise recovery reauthorization" in reopened_supervisory_recovery_investigation_contract()["traceability"]
