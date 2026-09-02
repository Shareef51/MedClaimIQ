from __future__ import annotations
from app.evaluation.regulatory_examination_reopened_supervisory_recovery_investigation import (
    reconstruct_multi_cycle_supervisory_evidence,
    reconstruct_persistent_emergent_root_causes,
    analyze_repeated_control_retransformation_failures,
    classify_enterprise_systemic_failure,
)

def run_reopened_supervisory_recovery_investigation_monitor(items: list[dict]) -> dict:
    alerts=[]
    for item in items:
        program_id=item.get("recovery_program_id")
        evidence=reconstruct_multi_cycle_supervisory_evidence(item.get("evidence_reconstruction", {}))
        roots=reconstruct_persistent_emergent_root_causes(item.get("root_cause_reconstruction", {}))
        controls=analyze_repeated_control_retransformation_failures(item.get("control_retransformation", {}))
        classification=classify_enterprise_systemic_failure(item.get("systemic_failure_classification", {}))
        if evidence["repeated_supervisory_failure_pattern"]:
            alerts.append({"recovery_program_id":program_id,"kind":"repeated_supervisory_recovery_failure","severity":"high"})
        if roots["persistent_systemic_root_cause_candidate"] or roots["emergent_systemic_root_cause_candidate"]:
            alerts.append({"recovery_program_id":program_id,"kind":"systemic_root_cause_candidate","severity":"critical"})
        if controls["enterprise_retransformation_failure_candidate"]:
            alerts.append({"recovery_program_id":program_id,"kind":"enterprise_control_retransformation_failure","severity":"high"})
        if classification["enterprise_systemic_failure_candidate"]:
            alerts.append({"recovery_program_id":program_id,"kind":"enterprise_systemic_failure_candidate","severity":"critical"})
    return {
        "monitoring_only": True,
        "automated_investigation_opening": False,
        "automated_root_cause_confirmation": False,
        "automated_systemic_failure_classification_confirmation": False,
        "automated_reauthorization": False,
        "automated_risk_acceptance": False,
        "automated_recovery_certification": False,
        "automated_reclosure": False,
        "alerts": alerts,
    }
