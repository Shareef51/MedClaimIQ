from pathlib import Path
from app.domain.regulatory_examination_reauthorized_recovery_execution import REAUTHORIZED_RECOVERY_EXECUTION_AUTHORITY,reauthorized_recovery_execution_contract
from app.evaluation.regulatory_examination_reauthorized_recovery_execution import execution_readiness
ROOT=Path(__file__).resolve().parents[1]
required=[
 "backend/app/domain/regulatory_examination_reauthorized_recovery_execution.py",
 "backend/app/evaluation/regulatory_examination_reauthorized_recovery_execution.py",
 "backend/app/services/regulatory_examination_reauthorized_recovery_execution.py",
 "backend/app/api/v1/regulatory_examination_reauthorized_recovery_execution.py",
 "backend/alembic/versions/0083_reg_exam_reauthorized_recovery_execution.py",
 "config/regulatory-reauthorized-recovery-execution-policy.json",
 "docs/regulatory-examination-reauthorized-recovery-execution.md",
]
assert all((ROOT/p).exists() for p in required)
a=REAUTHORIZED_RECOVERY_EXECUTION_AUTHORITY
assert not a["ai_can_approve_control_rerehabilitation"] and not a["ai_can_accept_residual_systemic_risk"] and not a["ai_can_certify_recovery_effectiveness"]
r=execution_readiness({"human_reauthorization_reference_present":True,"reauthorized_workstreams_defined":True,"control_rerehabilitation_scope_human_approved":True,"cross_entity_sequence_validated":True,"regulatory_commitment_alignment_complete":True,"critical_path_reviewed":True,"execution_evidence_current":True,"independent_recovery_assurance_complete":True})
assert r["execution_readiness_score"]==100.0 and r["ready_for_human_outcome_review"]
assert "independent recovery assurance" in reauthorized_recovery_execution_contract()["traceability"]
print("Release 88 verification passed")
