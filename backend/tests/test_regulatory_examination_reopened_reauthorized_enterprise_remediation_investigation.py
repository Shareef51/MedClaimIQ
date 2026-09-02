from app.domain.regulatory_examination_reopened_reauthorized_enterprise_remediation_investigation import (
    REOPENED_REAUTHORIZED_ENTERPRISE_REMEDIATION_INVESTIGATION_AUTHORITY,
    reopened_reauthorized_enterprise_remediation_investigation_contract,
)
from app.evaluation.regulatory_examination_reopened_reauthorized_enterprise_remediation_investigation import (
    reconstruct_multi_cycle_remediation_evidence,
    analyze_persistent_emergent_treatment_failure,
    reconstruct_systemic_remediation_failure_root_causes,
    validate_prior_recertification_reclosure_assumptions,
    analyze_repeated_systemic_control_retransformation_failures,
    classify_systemic_remediation_failure,
    enterprise_remediation_reauthorization_readiness,
)
from app.services.regulatory_examination_reopened_reauthorized_enterprise_remediation_investigation import (
    RegulatoryExaminationReopenedReauthorizedEnterpriseRemediationInvestigationService,
)


def test_release103_authority_boundary():
    a = REOPENED_REAUTHORIZED_ENTERPRISE_REMEDIATION_INVESTIGATION_AUTHORITY
    assert a["release102_human_enterprise_reopening_reference_required"]
    assert a["human_root_cause_confirmation_required"]
    assert a["independent_internal_audit_challenge_required"]
    assert not a["ai_can_confirm_root_cause"]
    assert not a["ai_can_authorize_enterprise_remediation"]
    assert not a["worker_can_open_authoritative_investigation"]
    assert not a["worker_can_authorize_enterprise_remediation"]


def test_release103_multi_cycle_evidence_treatment_failures_and_root_causes():
    evidence = reconstruct_multi_cycle_remediation_evidence({"cycles":[
        {"cycle_id":"c100","sequence":1,"status":"failed","evidence_refs":["e100"],"root_cause_treatment_version_id":"t100","independent_assurance_version_id":"a100"},
        {"cycle_id":"c101","sequence":2,"status":"recurred","evidence_refs":["e101"],"sustainability_reclosure_version_id":"r101"},
        {"cycle_id":"c102","sequence":3,"status":"remediation_failure","evidence_refs":["e102"],"enterprise_reopening_version_id":"o102"},
    ]})
    assert evidence["full_multi_cycle_remediation_evidence_reconstructed"]
    assert evidence["repeated_systemic_remediation_failure_pattern"]
    treatments = analyze_persistent_emergent_treatment_failure({"treatments":[
        {"treatment_id":"t1","root_cause_type":"persistent","current_status":"failed","evidence_refs":["e1"]},
        {"treatment_id":"t2","root_cause_type":"emergent","treatment_failed":True,"evidence_refs":["e2"]},
        {"treatment_id":"t3","root_cause_type":"persistent","current_status":"effective","evidence_refs":["e3"]},
    ]})
    assert treatments["material_root_cause_treatment_failure_candidate"]
    assert treatments["failed_persistent_treatment_ids"] == ["t1"]
    assert treatments["failed_emergent_treatment_ids"] == ["t2"]
    roots = reconstruct_systemic_remediation_failure_root_causes({
        "prior_confirmed_root_cause_ids":["r1"],"treated_root_cause_ids":["r1","r0"],"current_root_cause_ids":["r1","r2"],
        "failed_root_cause_treatment_count":2,"repeated_systemic_control_failure_count":3,"repeated_remediation_failure_cycle_count":3,
        "systemic_risk_rebound_confirmed":True,"cross_entity_recurrence_confirmed":True,
    })
    assert roots["persistent_systemic_remediation_failure_root_cause_ids"] == ["r1"]
    assert roots["emergent_systemic_remediation_failure_root_cause_ids"] == ["r2"]
    assert roots["persistent_systemic_root_cause_candidate"]


def test_release103_assumption_control_classification_and_readiness():
    assumptions = validate_prior_recertification_reclosure_assumptions({"assumptions":[
        {"assumption_id":"a1","current_status":"contradicted","root_cause_treatment_invalidated":True},
        {"assumption_id":"a2","current_status":"confirmed"},
    ]})
    assert assumptions["prior_recertification_reclosure_assumptions_at_risk"]
    controls = analyze_repeated_systemic_control_retransformation_failures({"controls":[
        {"control_id":"ctrl1","current_status":"failed","failure_cycle_count":3,"entity_ids":["US","EU"],"root_cause_ids":["r1"],"root_cause_treatment_ids":["t1"]},
        {"control_id":"ctrl2","retransformation_effective":False,"failure_cycle_count":2,"entity_ids":["APAC"]},
    ]})
    assert controls["enterprise_systemic_control_failure_candidate"] and len(controls["repeated_failure_control_ids"]) == 2
    classification = classify_systemic_remediation_failure({
        "systemic_remediation_failure_root_cause_risk_score":94,"failed_root_cause_treatment_count":4,
        "failed_systemic_control_retransformation_count":4,"affected_entity_count":4,"systemic_risk_rebound_percent":70,
        "repeated_remediation_failure_cycle_count":4,"breached_regulatory_commitment_count":2,"material_regulator_followup_count":2,
    })
    assert classification["enterprise_systemic_remediation_failure_candidate"]
    assert classification["human_classification_confirmation_required"]
    full = {
        "release102_human_enterprise_reopening_verified":True,"formal_reopened_remediation_investigation_complete":True,
        "full_multi_cycle_remediation_evidence_reconstructed":True,"persistent_emergent_treatment_failure_human_validated":True,
        "prior_recertification_reclosure_assumptions_validated":True,"systemic_remediation_failure_root_causes_human_confirmed":True,
        "repeated_systemic_control_retransformation_failure_assessed":True,"cross_entity_causal_propagation_human_validated":True,
        "regulatory_commitment_followup_impact_human_interpreted":True,"systemic_remediation_failure_classification_human_confirmed":True,
        "renewed_enterprise_remediation_strategy_documented":True,"independent_internal_audit_challenge_complete":True,
        "segregation_of_duties_confirmed":True,"executive_review_complete":True,"evidence_bound_reauthorization_package_complete":True,
    }
    ready = enterprise_remediation_reauthorization_readiness(full)
    assert ready["ready_for_human_enterprise_remediation_reauthorization"]
    assert ready["enterprise_remediation_reauthorization_readiness_score"] == 100.0
    assert not ready["automated_reauthorization_allowed"]


def test_release103_human_reopening_provenance_sod_and_executive_reauthorization_boundary():
    svc = RegulatoryExaminationReopenedReauthorizedEnterpriseRemediationInvestigationService(None, "tenant-a")
    base = {"actor_role":"ai_agent","recovery_program_id":"rp1","release102_enterprise_recovery_reopening_version_id":"op102","release102_human_enterprise_reopening_verified":True,"summary":"x","surveillance_version_refs":["s102"],"evidence_refs":["e1"]}
    try: svc.create_investigation("ai", base)
    except PermissionError: pass
    else: raise AssertionError("AI cannot open authoritative remediation investigation")
    base["actor_role"] = "internal_auditor"; base["release102_human_enterprise_reopening_verified"] = False
    try: svc.create_investigation("ia", base)
    except ValueError: pass
    else: raise AssertionError("verified Release 102 human reopening is mandatory")
    rc = svc.confirm_root_causes("ia", {"actor_role":"internal_auditor","recovery_program_id":"rp1","investigation_version_id":"inv103","root_cause_analysis_version_id":"rca103","confirmed_persistent_root_cause_ids":["r1"],"confirmed_emergent_root_cause_ids":["r2"],"conclusion":"confirmed","evidence_refs":["e1"]})
    assert rc["human_confirmation"] and not rc["automated_confirmation"]
    try:
        svc.independent_challenge("ia", {"reviewer_role":"internal_auditor","investigation_owner_actor_id":"ia","recovery_program_id":"rp1","investigation_version_id":"inv103","strategy_candidate_version_id":"st103","systemic_remediation_failure_classification_version_id":"sf103","decision":"challenge_not_sustained","rationale":"x","evidence_refs":["e1"]})
    except PermissionError: pass
    else: raise AssertionError("investigation owner cannot independently challenge own investigation")
    full = {
        "release102_human_enterprise_reopening_verified":True,"formal_reopened_remediation_investigation_complete":True,"full_multi_cycle_remediation_evidence_reconstructed":True,
        "persistent_emergent_treatment_failure_human_validated":True,"prior_recertification_reclosure_assumptions_validated":True,
        "systemic_remediation_failure_root_causes_human_confirmed":True,"repeated_systemic_control_retransformation_failure_assessed":True,
        "cross_entity_causal_propagation_human_validated":True,"regulatory_commitment_followup_impact_human_interpreted":True,
        "systemic_remediation_failure_classification_human_confirmed":True,"renewed_enterprise_remediation_strategy_documented":True,
        "independent_internal_audit_challenge_complete":True,"segregation_of_duties_confirmed":True,"executive_review_complete":True,
        "evidence_bound_reauthorization_package_complete":True,
    }
    payload = {"actor_role":"ai_agent","decision":"authorize","rationale":"x","recovery_program_id":"rp1","release102_enterprise_recovery_reopening_version_id":"op102","investigation_version_id":"inv103","investigation_conclusion_version_id":"con103","root_cause_confirmation_version_id":"rc103","systemic_remediation_failure_classification_version_id":"sf103","strategy_candidate_version_id":"st103","independent_challenge_version_id":"ch103","evidence_refs":["e1"],"readiness":full}
    try: svc.authorize_enterprise_remediation("ai", payload)
    except PermissionError: pass
    else: raise AssertionError("AI cannot reauthorize enterprise remediation")
    payload["actor_role"] = "chief_risk_officer"
    result = svc.authorize_enterprise_remediation("cro", payload)
    assert result["human_reauthorization"] and not result["automated_reauthorization"]
    assert "Release 102 human enterprise reopening" in reopened_reauthorized_enterprise_remediation_investigation_contract()["traceability"]
