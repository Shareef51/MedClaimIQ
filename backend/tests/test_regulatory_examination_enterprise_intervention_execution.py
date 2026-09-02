from app.domain.regulatory_examination_enterprise_intervention_execution import ENTERPRISE_INTERVENTION_EXECUTION_AUTHORITY, enterprise_intervention_execution_contract
from app.evaluation.regulatory_examination_enterprise_intervention_execution import program_execution_readiness, resource_capacity_risk, effectiveness_assurance, dependency_concentration
from app.services.regulatory_examination_enterprise_intervention_execution import RegulatoryExaminationEnterpriseInterventionExecutionService


def test_release74_non_delegable_authority():
    a=ENTERPRISE_INTERVENTION_EXECUTION_AUTHORITY
    assert a["ai_can_approve_remediation_program"] is False
    assert a["ai_can_certify_effectiveness"] is False
    assert a["ai_can_accept_residual_systemic_risk"] is False
    assert a["worker_can_certify_effectiveness"] is False


def test_release74_cross_entity_readiness_and_dependency_controls():
    p={"workstreams":[{"status":"completed"},{"status":"completed"}],"dependencies":[],"checkpoints":[{"evidence_complete":True},{"evidence_complete":True}],"required_entity_ids":["US","EU"],"validated_entity_ids":["US","EU"],"regulatory_commitment_links":[{"mapped":True}]}
    r=program_execution_readiness(p)
    assert r["readiness_score"]==100 and r["ready_for_independent_assurance"]
    p["dependencies"]=[{"status":"overdue"}]
    blocked=program_execution_readiness(p)
    assert not blocked["ready_for_independent_assurance"] and "blocked_or_overdue_dependencies" in blocked["blockers"]
    d=dependency_concentration({"workstreams":[{"workstream_id":"w1","dependency_ids":["dep1"]},{"workstream_id":"w2","dependency_ids":["dep1"]}]})
    assert d["concentration_detected"]


def test_release74_independent_effectiveness_and_capacity_risk():
    a=effectiveness_assurance({"independent_tests":[{"entity_id":"US","result":"pass"},{"entity_id":"EU","result":"pass"}],"required_entity_ids":["US","EU"],"residual_systemic_risk_score":20,"maximum_certifiable_residual_risk":25})
    assert a["eligible_for_human_executive_certification"] and a["automated_certification_allowed"] is False
    failed=effectiveness_assurance({"independent_tests":[{"entity_id":"US","result":"pass"},{"entity_id":"EU","result":"fail"}],"required_entity_ids":["US","EU"],"residual_systemic_risk_score":20})
    assert not failed["eligible_for_human_executive_certification"]
    risk=resource_capacity_risk({"available_capacity":10,"planned_demand":15,"critical_workstream_count":2,"overdue_milestone_count":1})
    assert risk["executive_attention_required"]


def test_release74_human_program_and_certification_boundaries():
    s=RegulatoryExaminationEnterpriseInterventionExecutionService(None,"tenant-a")
    try: s.create_program("ai",{"intervention_case_id":"ic1","program_name":"P","reviewer_role":"ai_agent","rationale":"x","executive_owner_user_id":"e1"})
    except PermissionError: pass
    else: raise AssertionError("AI cannot approve enterprise remediation program")
    program=s.create_program("cro",{"intervention_case_id":"ic1","program_name":"Enterprise Data Control Remediation","reviewer_role":"chief_risk_officer","rationale":"systemic recurrence","executive_owner_user_id":"exec1","workstreams":[]})
    assurance=s.independent_assurance("audit",{"intervention_program_id":program["intervention_program_id"],"reviewer_role":"internal_auditor","independent_tests":[{"entity_id":"US","result":"pass"}],"required_entity_ids":["US"],"residual_systemic_risk_score":15,"maximum_certifiable_residual_risk":25,"rationale":"effective"})
    try: s.executive_certification("ai",{"intervention_program_id":program["intervention_program_id"],"reviewer_role":"ai_agent","decision":"certify","rationale":"x","independent_assurance_version_id":assurance["independent_assurance_version_id"],"residual_systemic_risk_score":15})
    except PermissionError: pass
    else: raise AssertionError("AI cannot certify")
    cert=s.executive_certification("exec",{"intervention_program_id":program["intervention_program_id"],"reviewer_role":"executive_certifier","decision":"certify","rationale":"independent assurance passed","independent_assurance_version_id":assurance["independent_assurance_version_id"],"residual_systemic_risk_score":15,"evidence_refs":["ev1"]})
    assert cert["human_decision"] and cert["automated_certification"] is False
    assert len(cert["version_hash"])==64 and "independent testing" in enterprise_intervention_execution_contract()["traceability"]
