from app.domain.regulatory_examination_reopened_enterprise_intervention import REOPENED_ENTERPRISE_INTERVENTION_AUTHORITY, reopened_enterprise_intervention_contract
from app.evaluation.regulatory_examination_reopened_enterprise_intervention import root_cause_comparison, propagation_readiness, second_systemic_recurrence, reclosure_readiness
from app.services.regulatory_examination_reopened_enterprise_intervention import RegulatoryExaminationReopenedEnterpriseInterventionService

def test_release77_non_delegable_authority():
    a=REOPENED_ENTERPRISE_INTERVENTION_AUTHORITY
    assert a["ai_can_approve_remediation_program"] is False
    assert a["ai_can_accept_residual_systemic_risk"] is False
    assert a["ai_can_certify_effectiveness"] is False
    assert a["ai_can_reclose_intervention_program"] is False
    assert a["worker_can_approve_or_reclose"] is False

def test_release77_root_cause_propagation_and_second_recurrence():
    c=root_cause_comparison({"primary_root_cause_id":"r1","root_cause_ids":["r1"],"control_ids":["c1"]},{"primary_root_cause_id":"r1","root_cause_ids":["r1","r2"],"control_ids":["c1","c2"]})
    assert c["systemic_recurrence_supported"] and c["human_validation_required"]
    p=propagation_readiness({"required_entity_ids":["US","EU","APAC"],"completed_entity_ids":["US","EU"]})
    assert not p["cross_entity_propagation_complete"] and p["missing_entity_ids"]==["APAC"]
    r=second_systemic_recurrence([{"event_type":"systemic_recurrence","confirmed":True},{"event_type":"program_reopen","confirmed":True}])
    assert r["second_systemic_recurrence"] and r["internal_audit_escalation_required"]

def test_release77_reclosure_readiness_gates():
    ready=reclosure_readiness({"renewed_plan_human_approved":True,"all_milestones_complete":True,"cross_entity_remediation_complete":True,"regulator_commitments_reconciled":True,"evidence_complete":True,"independent_revalidation_passed":True,"sustainability_reset_complete":True,"human_residual_risk_reassessed":True,"second_systemic_recurrence_detected":False})
    assert ready["reclosure_readiness_score"]==100 and ready["ready_for_human_executive_recertification"]
    blocked=reclosure_readiness({"renewed_plan_human_approved":True,"all_milestones_complete":True,"cross_entity_remediation_complete":True,"regulator_commitments_reconciled":True,"evidence_complete":True,"independent_revalidation_passed":True,"sustainability_reset_complete":True,"human_residual_risk_reassessed":True,"second_systemic_recurrence_detected":True})
    assert not blocked["ready_for_human_executive_recertification"]

def test_release77_human_only_risk_and_reclosure():
    svc=RegulatoryExaminationReopenedEnterpriseInterventionService(None,"tenant-a")
    try: svc.residual_risk_reassessment("ai",{"reviewer_role":"ai_agent","residual_systemic_risk_score":20,"decision":"accept","rationale":"x","evidence_refs":[]})
    except PermissionError: pass
    else: raise AssertionError("AI cannot accept residual risk")
    rr=svc.residual_risk_reassessment("cro",{"reviewer_role":"chief_risk_officer","residual_systemic_risk_score":20,"decision":"accept","rationale":"bounded residual risk","evidence_refs":["ev1"]})
    rv=svc.independent_revalidation("audit",{"intervention_program_id":"p1","reviewer_role":"internal_auditor","result":"pass","rationale":"passed","evidence_refs":["ev2"],"tested_entity_ids":["US","EU"]})
    cert=svc.executive_recertification("exec",{"reviewer_role":"executive_certifier","decision":"certify","rationale":"all gates complete","readiness_score":100,"independent_revalidation_id":rv["independent_revalidation_version_id"],"residual_risk_reassessment_id":rr["residual_risk_reassessment_version_id"],"evidence_refs":["ev1","ev2"]})
    closed=svc.reclose_program("exec",{"reviewer_role":"executive_certifier","decision":"reclose","rationale":"sustained remediation","executive_recertification_id":cert["executive_recertification_version_id"],"sustainability_reset":{"days":365},"evidence_refs":["ev1","ev2"]})
    assert closed["human_decision"] and closed["automated_reclosure"] is False
    assert "executive reclosure" in reopened_enterprise_intervention_contract()["traceability"]
