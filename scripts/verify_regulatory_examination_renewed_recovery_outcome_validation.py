from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
required = [
    "backend/app/domain/regulatory_examination_renewed_recovery_outcome_validation.py",
    "backend/app/evaluation/regulatory_examination_renewed_recovery_outcome_validation.py",
    "backend/app/schemas/regulatory_examination_renewed_recovery_outcome_validation.py",
    "backend/app/services/regulatory_examination_renewed_recovery_outcome_validation.py",
    "backend/app/api/v1/regulatory_examination_renewed_recovery_outcome_validation.py",
    "backend/app/workers/regulatory_examination_renewed_recovery_outcome_validation.py",
    "backend/tests/test_regulatory_examination_renewed_recovery_outcome_validation.py",
    "backend/alembic/versions/0080_reg_exam_renewed_recovery_outcome_validation.py",
    "config/policies/regulatory-examination-renewed-recovery-outcome-validation.yaml",
    "sample-data/regulatory/renewed_recovery_outcome_validation_scenarios.json",
    "docs/regulatory-examination-renewed-recovery-outcome-validation.md",
]
for rel in required:
    if not (ROOT / rel).exists():
        raise SystemExit(f"missing {rel}")
main = (ROOT / "backend/app/main.py").read_text()
assert "regulatory_examination_renewed_recovery_outcome_validation_router" in main
cfg = (ROOT / "backend/app/core/config.py").read_text()
assert "regulatory_examination_renewed_recovery_outcome_validation_model_enabled" in cfg
migration = (ROOT / "backend/alembic/versions/0080_reg_exam_renewed_recovery_outcome_validation.py").read_text()
assert 'down_revision = "0079_reg_exam_renewed_recovery_execution"' in migration
print("release85 verification: PASS")
