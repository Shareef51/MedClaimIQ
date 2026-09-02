from app.domain.regulatory_examination_reopened_enterprise_recovery_investigation import (
    REOPENED_ENTERPRISE_RECOVERY_INVESTIGATION_AUTHORITY,
    reopened_enterprise_recovery_investigation_contract,
)
from app.evaluation.regulatory_examination_reopened_enterprise_recovery_investigation import (
    reconstruct_multi_cycle_enterprise_evidence,
    reconstruct_systemic_recovery_failure_root_causes,
    validate_prior_enterprise_recertification_reclosure_assumptions,
    analyze_repeated_systemic_control_retransformation_failures,
    classify_enterprise_systemic_failure,
    enterprise_remediation_reauthorization_readiness,
)
from app.services.regulatory_examination_reopened_enterprise_recovery_investigation import RegulatoryExaminationReopenedEnterpriseRecoveryInvestigationService


def test_release99_non_delegable_authority_and_release98_provenance():
    a=REOPENED_ENTERPRISE_RECOVERY_INVESTIGATION_AUTHORITY
    assert a["release98_human_enterprise_reopening_reference_required"]
    assert a["human_root_cause_confirmation_required"]
    assert a["human_systemic_failure_classification_confirmation_required"]
    assert a["segregation_of_duties_required"]
    assert not a["ai_can_authorize_enterprise_remediation"]
    assert not a["ai_can_confirm_root_cause"]
    assert not a["worker_can_authorize_enterprise_remediation"]


def test_release99_multi_cycle_evidence_and_systemic_root_causes():
    evidence=reconstruct_multi_cycle_enterprise_evidence({"cycles":[
        {"cycle_id":"c1","sequence":1,"status":"failed","evidence_refs":["e1"],"reclosure_version_id":"r1","independent_assurance_version_id":"a1"},
        {"cycle_id":"c2","sequence":2,"status":"recurred","evidence_refs":["e2"],"reopening_version_id":"o2","human_reauthorization_version_id":"h2"},
        {"cycle_id":"c3","sequence":3,"status":"systemic_failure","evidence_refs":["e3"],"reclosure_version_id":"r3"},
    ]})
    assert evidence["full_multi_cycle_enterprise_evidence_reconstructed"]
    assert evidence["repeated_enterprise_recovery_failure_pattern"]
    roots=reconstruct_systemic_recovery_failure_root_causes({
        "prior_root_cause_ids":["r1"],"historical_root_cause_ids":["r0","r1"],"current_root_cause_ids":["r1","r2"],
        "repeated_systemic_control_failure_count":3,"repeated_recovery_failure_cycle_count":3,
        "systemic_risk_rebound_confirmed":True,"cross_entity_recurrence_confirmed":True,
    })
    assert roots["persistent_systemic_root_cause_ids"] == ["r1"]
    assert roots["emergent_systemic_root_cause_ids"] == ["r2"]
    assert roots["persistent_systemic_root_cause_candidate"]


def test_release99_assumptions_controls_classification_and_readiness():
    assumptions=validate_prior_enterprise_recertification_reclosure_assumptions({"assumptions":[
        {"assumption_id":"a1","current_status":"contradicted"},{"assumption_id":"a2","current_status":"confirmed"}
    ]})
    assert assumptions["prior_enterprise_recertification_reclosure_assumptions_at_risk"]
    controls=analyze_repeated_systemic_control_retransformation_failures({"controls":[
        {"control_id":"ctrl1","status":"failed","failure_cycle_count":3,"entity_ids":["US","EU"],"root_cause_ids":["r1"]},
        {"control_id":"ctrl2","retransformation_effective":False,"failure_cycle_count":2,"entity_ids":["APAC"]},
    ]})
    assert controls["enterprise_systemic_control_failure_candidate"] and len(controls["repeated_failure_control_ids"]) == 2
    classification=classify_enterprise_systemic_failure({"systemic_recovery_failure_root_cause_risk_score":92,"failed_systemic_control_retransformation_count":4,"affected_entity_count":4,"systemic_risk_rebound_percent":70,"repeated_failure_cycle_count":4,"breached_regulatory_commitment_count":2,"material_regulator_followup_count":2})
    assert classification["enterprise_systemic_failure_candidate"] and classification["human_classification_confirmation_required"]
    full={
        "release98_human_enterprise_reopening_verified":True,"formal_reopened_enterprise_investigation_complete":True,
        "full_multi_cycle_enterprise_evidence_reconstructed":True,"prior_enterprise_recertification_reclosure_assumptions_validated":True,
        "persistent_emergent_systemic_root_causes_human_confirmed":True,"repeated_systemic_control_retransformation_failure_assessed":True,
        "cross_entity_causal_propagation_human_validated":True,"regulatory_commitment_followup_impact_human_interpreted":True,
        "enterprise_systemic_failure_classification_human_confirmed":True,"renewed_enterprise_remediation_strategy_documented":True,
        "independent_internal_audit_challenge_complete":True,"segregation_of_duties_confirmed":True,
        "executive_review_complete":True,"evidence_bound_reauthorization_package_complete":True,
    }
    ready=enterprise_remediation_reauthorization_readiness(full)
    assert ready["ready_for_human_enterprise_remediation_reauthorization"] and ready["enterprise_remediation_reauthorization_readiness_score"] == 100.0
    assert not ready["automated_reauthorization_allowed"]


def test_release99_human_investigation_sod_and_executive_reauthorization_boundary():
    svc=RegulatoryExaminationReopenedEnterpriseRecoveryInvestigationService(None,"tenant-a")
    base={"actor_role":"ai_agent","recovery_program_id":"rp1","release98_enterprise_reopening_version_id":"op98","summary":"x","surveillance_version_refs":["s98"],"evidence_refs":["e1"]}
    try: svc.create_investigation("ai",base)
    except PermissionError: pass
    else: raise AssertionError("AI cannot open authoritative enterprise recovery investigation")
    base["actor_role"]="internal_auditor"; base["release98_enterprise_reopening_version_id"]=""
    try: svc.create_investigation("ia",base)
    except ValueError: pass
    else: raise AssertionError("Release 98 human reopening reference is mandatory")
    rc=svc.confirm_root_causes("ia",{"actor_role":"internal_auditor","recovery_program_id":"rp1","investigation_version_id":"inv99","root_cause_analysis_version_id":"rca99","confirmed_persistent_systemic_root_cause_ids":["r1"],"confirmed_emergent_systemic_root_cause_ids":["r2"],"conclusion":"confirmed","evidence_refs":["e1"]})
    assert rc["human_confirmation"] and not rc["automated_confirmation"]
    try:
        svc.independent_challenge("ia",{"reviewer_role":"internal_auditor","investigation_owner_actor_id":"ia","recovery_program_id":"rp1","investigation_version_id":"inv99","strategy_candidate_version_id":"st99","systemic_failure_classification_version_id":"sf99","decision":"challenge_not_sustained","rationale":"x","evidence_refs":["e1"]})
    except PermissionError: pass
    else: raise AssertionError("investigation owner cannot independently challenge own investigation")
    full={
        "release98_human_enterprise_reopening_verified":True,"formal_reopened_enterprise_investigation_complete":True,"full_multi_cycle_enterprise_evidence_reconstructed":True,
        "prior_enterprise_recertification_reclosure_assumptions_validated":True,"persistent_emergent_systemic_root_causes_human_confirmed":True,
        "repeated_systemic_control_retransformation_failure_assessed":True,"cross_entity_causal_propagation_human_validated":True,
        "regulatory_commitment_followup_impact_human_interpreted":True,"enterprise_systemic_failure_classification_human_confirmed":True,
        "renewed_enterprise_remediation_strategy_documented":True,"independent_internal_audit_challenge_complete":True,"segregation_of_duties_confirmed":True,
        "executive_review_complete":True,"evidence_bound_reauthorization_package_complete":True,
    }
    payload={"actor_role":"ai_agent","decision":"authorize","rationale":"x","recovery_program_id":"rp1","release98_enterprise_reopening_version_id":"op98","investigation_version_id":"inv99","investigation_conclusion_version_id":"con99","root_cause_confirmation_version_id":"rc99","systemic_failure_classification_version_id":"sf99","strategy_candidate_version_id":"st99","independent_challenge_version_id":"ch99","evidence_refs":["e1"],"readiness":full}
    try: svc.authorize_enterprise_remediation("ai",payload)
    except PermissionError: pass
    else: raise AssertionError("AI cannot reauthorize enterprise remediation")
    payload["actor_role"]="chief_risk_officer"
    result=svc.authorize_enterprise_remediation("cro",payload)
    assert result["human_reauthorization"] and not result["automated_reauthorization"]
    assert "human enterprise remediation reauthorization" in reopened_enterprise_recovery_investigation_contract()["traceability"]
