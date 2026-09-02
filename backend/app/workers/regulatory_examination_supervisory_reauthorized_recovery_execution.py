from app.evaluation.regulatory_examination_supervisory_reauthorized_recovery_execution import (
    control_retransformation_status,
    deployment_sequence_assessment,
    critical_path_assessment,
    implementation_drift,
    recovery_kpi_assessment,
    independent_recovery_assurance,
)


def run_supervisory_reauthorized_recovery_execution_monitor(items: list[dict]) -> dict:
    alerts = []
    for item in items:
        controls = control_retransformation_status(item)
        seq = deployment_sequence_assessment(item)
        critical = critical_path_assessment(item)
        drift = implementation_drift(item)
        kpi = recovery_kpi_assessment(item)
        assurance = independent_recovery_assurance(item)
        if (
            controls["missing_human_approval_count"]
            or controls["missing_release91_scope_reference_count"]
            or seq["sequence_at_risk"]
            or critical["critical_path_at_risk"]
            or drift["material_drift"]
            or (kpi["metric_count"] and not kpi["recovery_target_met"])
            or (assurance["test_count"] and not assurance["assurance_passed"])
        ):
            alerts.append({
                "recovery_program_id": item.get("recovery_program_id"),
                "human_review_required": True,
                "control_approval_gap": bool(controls["missing_human_approval_count"]),
                "release91_scope_gap": bool(controls["missing_release91_scope_reference_count"]),
                "sequence_at_risk": seq["sequence_at_risk"],
                "critical_path_at_risk": critical["critical_path_at_risk"],
                "material_drift": drift["material_drift"],
                "recovery_target_met": kpi["recovery_target_met"],
                "independent_assurance_passed": assurance["assurance_passed"],
            })
    return {
        "monitoring_only": True,
        "automated_control_approval": False,
        "automated_recovery_certification": False,
        "automated_risk_acceptance": False,
        "automated_commitment_closure": False,
        "automated_program_reclosure": False,
        "alerts": alerts,
    }
