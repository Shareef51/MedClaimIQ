from __future__ import annotations
from app.evaluation.regulatory_examination_reopened_reauthorized_recovery_investigation import (
    reconstruct_reopened_recovery_cycles,
    reconstruct_repeated_failure_root_causes,
    analyze_re_rehabilitation_failures,
)

def run_reopened_reauthorized_recovery_investigation_monitor(items: list[dict]) -> dict:
    alerts = []
    for item in items:
        program_id = item.get("recovery_program_id")
        evidence = reconstruct_reopened_recovery_cycles(item.get("evidence_reconstruction", {}))
        roots = reconstruct_repeated_failure_root_causes(item.get("root_cause_reconstruction", {}))
        rehab = analyze_re_rehabilitation_failures(item.get("re_rehabilitation", {}))
        if evidence["repeated_failure_pattern"]:
            alerts.append({"recovery_program_id": program_id, "kind": "repeated_recovery_failure", "severity": "high"})
        if roots["persistent_systemic_cause_candidate"]:
            alerts.append({"recovery_program_id": program_id, "kind": "persistent_systemic_root_cause_candidate", "severity": "critical"})
        if rehab["enterprise_re_rehabilitation_failure"]:
            alerts.append({"recovery_program_id": program_id, "kind": "enterprise_re_rehabilitation_failure", "severity": "high"})
    return {
        "monitoring_only": True,
        "automated_investigation_opening": False,
        "automated_reauthorization": False,
        "automated_risk_acceptance": False,
        "automated_reclosure": False,
        "alerts": alerts,
    }
