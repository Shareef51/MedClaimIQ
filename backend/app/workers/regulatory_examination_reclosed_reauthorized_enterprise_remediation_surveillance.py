from app.evaluation.regulatory_examination_reclosed_reauthorized_enterprise_remediation_surveillance import (
    multi_cycle_enterprise_recovery_decay,
    root_cause_treatment_decay,
    systemic_control_retransformation_regression,
    systemic_risk_rebound,
    cross_entity_recurrence,
    examination_finding_correlation,
    regulator_followup_linkage,
    enterprise_materiality,
)


def run_reclosed_reauthorized_enterprise_remediation_surveillance_monitor(items: list[dict]) -> dict:
    alerts = []
    for item in items:
        decay = multi_cycle_enterprise_recovery_decay(item)
        treatment_decay = root_cause_treatment_decay(item)
        regression = systemic_control_retransformation_regression(item)
        rebound = systemic_risk_rebound(item)
        recurrence = cross_entity_recurrence(item)
        findings = examination_finding_correlation(item)
        followups = regulator_followup_linkage(item)
        materiality = enterprise_materiality({
            **item,
            **decay,
            **treatment_decay,
            **regression,
            **rebound,
            **recurrence,
            "adverse_regulator_followup_count": followups["adverse_linked_followup_count"],
        })
        if (
            decay["human_investigation_required"]
            or treatment_decay["material_root_cause_treatment_decay_candidate"]
            or regression["material_systemic_control_regression_candidate"]
            or rebound["material_systemic_risk_rebound_candidate"]
            or recurrence["cross_entity_recurrence_propagation"]
            or findings["new_examination_finding_correlation"]
            or followups["regulator_followup_escalation_candidate"]
            or materiality["enterprise_reopening_candidate"]
        ):
            alerts.append({
                "recovery_program_id": item.get("recovery_program_id"),
                "human_review_required": True,
                "multi_cycle_enterprise_recovery_decay_score": decay["multi_cycle_enterprise_recovery_decay_score"],
                "root_cause_treatment_decay_percent": treatment_decay["root_cause_treatment_decay_percent"],
                "material_systemic_control_regression_candidate": regression["material_systemic_control_regression_candidate"],
                "material_systemic_risk_rebound_candidate": rebound["material_systemic_risk_rebound_candidate"],
                "cross_entity_recurrence_propagation": recurrence["cross_entity_recurrence_propagation"],
                "enterprise_materiality_tier": materiality["enterprise_materiality_tier"],
                "executive_internal_audit_escalation_required": materiality["executive_internal_audit_escalation_required"],
            })
    return {
        "monitoring_only": True,
        "automated_investigation_opening": False,
        "automated_reopening": False,
        "automated_reclosure": False,
        "automated_recovery_certification": False,
        "automated_risk_acceptance": False,
        "automated_commitment_closure": False,
        "alerts": alerts,
    }
