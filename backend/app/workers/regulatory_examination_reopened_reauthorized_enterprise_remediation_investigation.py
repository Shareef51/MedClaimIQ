from __future__ import annotations
from app.evaluation.regulatory_examination_reopened_reauthorized_enterprise_remediation_investigation import (
    reconstruct_multi_cycle_remediation_evidence,
    analyze_persistent_emergent_treatment_failure,
    reconstruct_systemic_remediation_failure_root_causes,
    analyze_repeated_systemic_control_retransformation_failures,
    assess_regulatory_commitment_followup_impact,
    classify_systemic_remediation_failure,
)

def run_reopened_reauthorized_enterprise_remediation_investigation_monitor(items: list[dict]) -> dict:
    alerts=[]
    for item in items:
        program_id=item.get("recovery_program_id")
        evidence=reconstruct_multi_cycle_remediation_evidence(item.get("evidence_reconstruction", {}))
        treatments=analyze_persistent_emergent_treatment_failure(item.get("treatment_failure", {}))
        roots=reconstruct_systemic_remediation_failure_root_causes(item.get("root_cause_reconstruction", {}))
        controls=analyze_repeated_systemic_control_retransformation_failures(item.get("control_retransformation", {}))
        impact=assess_regulatory_commitment_followup_impact(item.get("regulatory_impact", {}))
        classification=classify_systemic_remediation_failure(item.get("systemic_failure_classification", {}))
        if evidence["repeated_systemic_remediation_failure_pattern"]:
            alerts.append({"recovery_program_id":program_id,"kind":"repeated_systemic_remediation_failure","severity":"critical"})
        if treatments["material_root_cause_treatment_failure_candidate"]:
            alerts.append({"recovery_program_id":program_id,"kind":"root_cause_treatment_failure_candidate","severity":"critical"})
        if roots["persistent_systemic_root_cause_candidate"] or roots["emergent_systemic_root_cause_candidate"]:
            alerts.append({"recovery_program_id":program_id,"kind":"systemic_remediation_root_cause_candidate","severity":"critical"})
        if controls["enterprise_systemic_control_failure_candidate"]:
            alerts.append({"recovery_program_id":program_id,"kind":"systemic_control_retransformation_failure","severity":"critical"})
        if impact["material_regulatory_impact_candidate"]:
            alerts.append({"recovery_program_id":program_id,"kind":"material_regulatory_commitment_followup_impact","severity":"high"})
        if classification["enterprise_systemic_remediation_failure_candidate"]:
            alerts.append({"recovery_program_id":program_id,"kind":"systemic_remediation_failure_candidate","severity":"critical"})
    return {
        "monitoring_only": True,
        "automated_investigation_opening": False,
        "automated_root_cause_confirmation": False,
        "automated_systemic_remediation_failure_classification_confirmation": False,
        "automated_remediation_reauthorization": False,
        "automated_residual_risk_acceptance": False,
        "automated_recovery_certification": False,
        "automated_commitment_closure": False,
        "automated_program_reclosure": False,
        "alerts": alerts,
    }
