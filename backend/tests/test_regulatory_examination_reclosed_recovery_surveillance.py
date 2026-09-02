import pytest
from app.domain.regulatory_examination_reclosed_recovery_surveillance import reclosed_recovery_surveillance_contract
from app.evaluation.regulatory_examination_reclosed_recovery_surveillance import surveillance_score, reopening_readiness, examination_match_score
from app.services.regulatory_examination_reclosed_recovery_surveillance import RegulatoryExaminationReclosedRecoverySurveillanceService

def test_authority_boundary():
    a=reclosed_recovery_surveillance_contract()["authority"]
    assert a["ai_can_reopen_program"] is False
    assert a["ai_can_accept_residual_systemic_risk"] is False
    assert a["ai_can_certify_recovery_effectiveness"] is False

def test_systemic_recovery_decay_and_cross_entity_regression():
    s=surveillance_score({"closure_residual_risk_score":20,"current_systemic_risk_score":35,"closure_control_effectiveness":95,"current_control_effectiveness":75,"expected_entity_ids":["US","EU"],"regressed_entity_ids":["EU"]})
    assert "systemic_risk_rebound" in s["signals"]
    assert "recovery_effectiveness_decay" in s["signals"]
    assert s["cross_entity_regression_percent"] == 50.0
    assert s["human_investigation_required"] is True

def test_examination_matching_requires_human_validation():
    m=examination_match_score({"root_cause_similarity":.9,"control_overlap":.8,"entity_overlap":.7,"regulatory_obligation_overlap":.9})
    assert m["closed_program_match_candidate"] is True
    assert m["human_validation_required"] is True

def test_human_only_enterprise_reopening_and_full_gates():
    svc=RegulatoryExaminationReclosedRecoverySurveillanceService(None,"t1")
    ready={"sustainability_breach_confirmed":True,"investigation_complete":True,"independent_reassessment_complete":True,"executive_review_complete":True,"internal_audit_review_complete":True,"prior_certification_compared":True,"renewed_remediation_candidate_prepared":True}
    assert reopening_readiness(ready)["ready_for_human_enterprise_reopening"] is True
    with pytest.raises(PermissionError):
        svc.decide_reopening("ai",{"actor_role":"ai_agent","decision":"reopen","rationale":"x","readiness":ready})
    result=svc.decide_reopening("exec-1",{"actor_role":"chief_risk_officer","decision":"reopen","rationale":"confirmed systemic recovery decay","readiness":ready})
    assert result["human_reopening"] is True and result["automated_reopening"] is False
