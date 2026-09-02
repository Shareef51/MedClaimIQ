from app.domain.regulatory_examination_systemic_recurrence_portfolio import SYSTEMIC_RECURRENCE_PORTFOLIO_AUTHORITY, systemic_recurrence_portfolio_contract
from app.evaluation.regulatory_examination_systemic_recurrence_portfolio import aggregate_systemic_patterns, supervisory_materiality_score, correlate_regulator_followups
from app.services.regulatory_examination_systemic_recurrence_portfolio import RegulatoryExaminationSystemicRecurrencePortfolioService

def _occurrences():
    return [
        {"commitment_id":"c1","root_cause_id":"r1","control_id":"ctrl1","entity_id":"US","examination_id":"e1","regulator":"R1"},
        {"commitment_id":"c2","root_cause_id":"r1","control_id":"ctrl1","entity_id":"EU","examination_id":"e2","regulator":"R2"},
        {"commitment_id":"c3","root_cause_id":"r1","control_id":"ctrl2","entity_id":"APAC","examination_id":"e3","regulator":"R1"},
    ]

def test_release73_non_delegable_authority():
    a=SYSTEMIC_RECURRENCE_PORTFOLIO_AUTHORITY
    assert a["ai_can_declare_authoritative_regulatory_conclusion"] is False
    assert a["ai_can_approve_intervention_program"] is False
    assert a["worker_can_approve_intervention_program"] is False

def test_release73_systemic_aggregation_and_followup_correlation():
    agg=aggregate_systemic_patterns(_occurrences())
    assert agg["systemic_pattern_candidate"] and agg["recurring_commitment_count"]==3
    assert agg["affected_entity_count"]==3 and agg["shared_root_causes"][0]["root_cause_id"]=="r1"
    f=correlate_regulator_followups(_occurrences(),[{"commitment_id":"c1","overdue":True},{"commitment_id":"c2","overdue":False}])
    assert f["linked_occurrence_count"]==2 and f["overdue_follow_up_count"]==1

def test_release73_materiality_drives_human_supervisory_intervention():
    m=supervisory_materiality_score({"recurring_commitment_count":8,"affected_entity_count":6,"affected_control_count":5,"affected_examination_count":5,"regulator_count":3,"critical_control_count":4,"overdue_follow_up_count":3,"repeated_root_cause":True})
    assert m["materiality_score"]>=80
    assert m["enterprise_intervention_required"] and m["internal_audit_challenge_required"]
    assert m["authoritative_regulatory_conclusion"] is False

def test_release73_human_intervention_program_and_independent_challenge():
    s=RegulatoryExaminationSystemicRecurrencePortfolioService(None,"tenant-a")
    try: s.create_intervention("u",{"portfolio_id":"p","systemic_pattern_id":"sp","reviewer_role":"analyst","rationale":"x"})
    except PermissionError: pass
    else: raise AssertionError("analyst cannot create governed intervention")
    case=s.create_intervention("u",{"portfolio_id":"p","systemic_pattern_id":"sp","reviewer_role":"chief_risk_officer","rationale":"systemic recurrence","evidence_refs":["e1"]})
    try: s.decide_program("u",{"intervention_case_id":case["intervention_case_id"],"reviewer_role":"ai_agent","decision":"approve","rationale":"x"})
    except PermissionError: pass
    else: raise AssertionError("AI cannot approve intervention program")
    decision=s.decide_program("exec",{"intervention_case_id":case["intervention_case_id"],"reviewer_role":"executive_certifier","decision":"approve","rationale":"enterprise remediation required"})
    challenge=s.independent_challenge("audit",{"intervention_case_id":case["intervention_case_id"],"reviewer_role":"internal_auditor","conclusion":"challenge_complete","rationale":"independent review","evidence_refs":["e2"]})
    assert decision["human_decision"] and decision["automated_approval"] is False
    assert challenge["independent_human_challenge"] and len(challenge["version_hash"])==64
    assert "enterprise risk" in systemic_recurrence_portfolio_contract()["traceability"]
