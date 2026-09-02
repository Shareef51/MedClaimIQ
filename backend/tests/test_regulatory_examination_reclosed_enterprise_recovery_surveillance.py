from app.domain.regulatory_examination_reclosed_enterprise_recovery_surveillance import (
    RECLOSED_ENTERPRISE_RECOVERY_SURVEILLANCE_AUTHORITY,
    reclosed_enterprise_recovery_surveillance_contract,
)
from app.evaluation.regulatory_examination_reclosed_enterprise_recovery_surveillance import (
    multi_cycle_enterprise_recovery_decay,
    systemic_control_retransformation_regression,
    systemic_risk_rebound,
    cross_entity_recurrence,
    prior_enterprise_reclosure_comparison,
    enterprise_materiality,
    enterprise_reopening_readiness,
)
from app.services.regulatory_examination_reclosed_enterprise_recovery_surveillance import (
    RegulatoryExaminationReclosedEnterpriseRecoverySurveillanceService,
)


def test_release98_non_delegable_authority_and_release97_provenance():
    authority = RECLOSED_ENTERPRISE_RECOVERY_SURVEILLANCE_AUTHORITY
    assert authority["release97_enterprise_sustainability_reclosure_reference_required"]
    assert authority["independent_reassessment_required"]
    assert authority["human_reopening_decision_required"]
    assert authority["segregation_of_duties_required"]
    assert not authority["ai_can_open_authoritative_investigation"]
    assert not authority["ai_can_reopen_program"]
    assert not authority["ai_can_accept_residual_systemic_risk"]
    assert not authority["worker_can_reopen_program"]
    service = RegulatoryExaminationReclosedEnterpriseRecoverySurveillanceService(None, "tenant-a")
    try:
        service.decay({"recovery_program_id": "rp1"})
    except ValueError:
        pass
    else:
        raise AssertionError("Release 97 enterprise sustainability reclosure provenance must be mandatory")


def test_release98_multi_cycle_decay_systemic_regression_rebound_and_recurrence():
    decay = multi_cycle_enterprise_recovery_decay({
        "release97_reclosure_control_health_score": 96,
        "current_control_health_score": 64,
        "systemic_control_retransformation_regressions": 2,
        "prior_enterprise_recovery_failure_cycles": 3,
        "sustainability_breach_count": 1,
        "regulatory_commitment_breach_count": 1,
    })
    assert decay["multi_cycle_enterprise_recovery_decay_score"] >= 50
    assert decay["repeated_enterprise_recovery_failure_candidate"]
    assert decay["human_investigation_required"]

    regression = systemic_control_retransformation_regression({"controls": [
        {"control_id": "c1", "release97_reclosure_status": "effective", "current_status": "failed", "severity": "critical", "post_reclosure_failure_count": 2, "evidence_refs": ["e1"]},
        {"control_id": "c2", "current_status": "effective", "evidence_refs": ["e2"]},
    ]})
    assert regression["material_systemic_control_regression_candidate"]
    assert regression["regressed_control_ids"] == ["c1"]
    assert regression["repeated_failure_regressed_control_ids"] == ["c1"]

    rebound = systemic_risk_rebound({
        "release97_reclosure_systemic_risk_score": 20,
        "current_systemic_risk_score": 38,
        "peak_post_reclosure_systemic_risk_score": 42,
    })
    assert rebound["material_systemic_risk_rebound_candidate"]
    assert rebound["systemic_risk_rebound_percent"] == 90.0

    recurrence = cross_entity_recurrence({
        "expected_entity_count": 4,
        "entities": [
            {"entity_id": "US", "status": "failed", "severity": "critical", "evidence_refs": ["e1"]},
            {"entity_id": "EU", "post_reclosure_failure_count": 2, "evidence_refs": ["e2"]},
        ],
    })
    assert recurrence["cross_entity_recurrence_propagation"]
    assert recurrence["cross_entity_recurrence_percent"] == 50.0


def test_release98_prior_reclosure_materiality_and_reopening_readiness():
    comparison = prior_enterprise_reclosure_comparison({
        "prior": {
            "control_health_score": 95,
            "systemic_risk_score": 20,
            "control_ids": ["c1"],
            "root_cause_ids": ["r1"],
            "entity_ids": ["US"],
            "enterprise_recovery_recertification_version_id": "rc1",
            "enterprise_sustainability_reclosure_version_id": "sr1",
        },
        "current": {
            "control_health_score": 69,
            "systemic_risk_score": 41,
            "control_ids": ["c1"],
            "root_cause_ids": ["r1"],
            "entity_ids": ["US"],
        },
    })
    assert comparison["prior_enterprise_reclosure_degradation_candidate"]
    assert comparison["repeated_root_cause_ids"] == ["r1"]

    materiality = enterprise_materiality({
        "multi_cycle_enterprise_recovery_decay_score": 82,
        "systemic_control_retransformation_regression_percent": 50,
        "cross_entity_recurrence_percent": 50,
        "systemic_risk_rebound_percent": 90,
        "prior_enterprise_recovery_failure_cycles": 3,
        "adverse_regulator_followup_count": 1,
        "regulatory_commitment_breach_count": 1,
    })
    assert materiality["enterprise_materiality_tier"] in {"enterprise_high", "enterprise_critical"}
    assert materiality["executive_internal_audit_escalation_required"]
    assert materiality["enterprise_reopening_candidate"]

    readiness = enterprise_reopening_readiness({
        "release97_enterprise_sustainability_reclosure_reference_validated": True,
        "material_systemic_recovery_decay_confirmed": True,
        "human_investigation_complete": True,
        "independent_reassessment_complete": True,
        "prior_executive_recertification_reclosure_compared": True,
        "cross_entity_recurrence_scope_validated": True,
        "new_examination_finding_links_human_validated": True,
        "regulator_followups_human_interpreted": True,
        "enterprise_materiality_human_validated": True,
        "executive_review_complete": True,
        "internal_audit_challenge_complete": True,
        "renewed_enterprise_recovery_governance_candidate_prepared": True,
    })
    assert readiness["ready_for_human_enterprise_reopening"]
    assert readiness["enterprise_reopening_readiness_score"] == 100.0


def test_release98_human_only_investigation_independent_reassessment_and_reopening():
    service = RegulatoryExaminationReclosedEnterpriseRecoverySurveillanceService(None, "tenant-a")
    try:
        service.create_investigation("ai", {
            "actor_role": "ai_agent",
            "recovery_program_id": "rp1",
            "release97_enterprise_sustainability_reclosure_version_id": "sr1",
            "summary": "systemic decay candidate",
            "surveillance_version_refs": ["sv1"],
            "evidence_refs": ["e1"],
        })
    except PermissionError:
        pass
    else:
        raise AssertionError("AI cannot open authoritative enterprise recovery investigation")

    try:
        service.independent_reassess("owner-1", {
            "actor_role": "internal_auditor",
            "recovery_program_id": "rp1",
            "result": "confirmed_decay",
            "conclusion": "systemic degradation confirmed",
            "investigation_version_id": "i1",
            "investigation_owner_id": "owner-1",
            "evidence_refs": ["e1"],
        })
    except PermissionError:
        pass
    else:
        raise AssertionError("segregation of duties must block investigation owner from independent reassessment")

    reassessment = service.independent_reassess("ia1", {
        "actor_role": "internal_auditor",
        "recovery_program_id": "rp1",
        "result": "confirmed_decay",
        "conclusion": "systemic degradation confirmed",
        "investigation_version_id": "i1",
        "investigation_owner_id": "owner-1",
        "evidence_refs": ["e1"],
    })
    assert reassessment["human_reassessment"] and not reassessment["automated_reassessment"]

    try:
        service.decide_reopening("ai", {
            "actor_role": "ai_agent",
            "decision": "reopen",
            "recovery_program_id": "rp1",
            "release97_enterprise_sustainability_reclosure_version_id": "sr1",
            "investigation_version_id": "i1",
            "independent_reassessment_version_id": "ir1",
            "enterprise_challenge_version_id": "ec1",
            "readiness": {},
        })
    except PermissionError:
        pass
    else:
        raise AssertionError("AI cannot reopen enterprise recovery program")

    assert "human enterprise reopening" in reclosed_enterprise_recovery_surveillance_contract()["traceability"]
