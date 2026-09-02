from pathlib import Path
from app.domain.regulatory_examination_supervisory_reauthorized_recovery_execution import SUPERVISORY_REAUTHORIZED_RECOVERY_EXECUTION_AUTHORITY, supervisory_reauthorized_recovery_execution_contract
from app.evaluation.regulatory_examination_supervisory_reauthorized_recovery_execution import execution_readiness, independent_recovery_assurance

ROOT = Path(__file__).resolve().parents[1]
required = [
    "backend/app/domain/regulatory_examination_supervisory_reauthorized_recovery_execution.py",
    "backend/app/evaluation/regulatory_examination_supervisory_reauthorized_recovery_execution.py",
    "backend/app/schemas/regulatory_examination_supervisory_reauthorized_recovery_execution.py",
    "backend/app/services/regulatory_examination_supervisory_reauthorized_recovery_execution.py",
    "backend/app/api/v1/regulatory_examination_supervisory_reauthorized_recovery_execution.py",
    "backend/app/workers/regulatory_examination_supervisory_reauthorized_recovery_execution.py",
    "backend/alembic/versions/0087_reg_exam_supervisory_reauthorized_recovery_execution.py",
    "config/regulatory-supervisory-reauthorized-recovery-execution-policy.json",
    "sample-data/regulatory/supervisory_reauthorized_recovery_execution_scenarios.json",
    "docs/regulatory-examination-supervisory-reauthorized-recovery-execution.md",
]
assert all((ROOT / p).exists() for p in required)
a = SUPERVISORY_REAUTHORIZED_RECOVERY_EXECUTION_AUTHORITY
assert a["release91_supervisory_reauthorization_reference_required"]
assert not a["ai_can_approve_control_retransformation"] and not a["ai_can_accept_residual_systemic_risk"] and not a["ai_can_certify_recovery_effectiveness"]
ready = execution_readiness({
    "release91_supervisory_reauthorization_reference_present": True,
    "supervisory_workstreams_defined": True,
    "control_retransformation_scope_human_approved": True,
    "cross_entity_sequence_validated": True,
    "regulatory_commitment_alignment_complete": True,
    "critical_path_reviewed": True,
    "execution_evidence_current": True,
    "recovery_kpis_baselined": True,
    "independent_recovery_assurance_complete": True,
})
assert ready["execution_readiness_score"] == 100.0 and ready["ready_for_human_outcome_review"]
assurance = independent_recovery_assurance({"tests":[{"result":"pass","independent_reviewer_id":"ia","release91_reauthorization_scope_validated":True,"cross_entity_effectiveness_validated":True,"repeated_failure_scope_validated":True}]})
assert assurance["assurance_passed"] and not assurance["automated_certification_allowed"]
assert "Release 91 human supervisory recovery reauthorization" in supervisory_reauthorized_recovery_execution_contract()["traceability"]
print("Release 92 verification passed")
