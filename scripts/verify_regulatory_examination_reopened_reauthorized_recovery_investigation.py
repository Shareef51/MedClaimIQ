from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
required = [
    "backend/app/domain/regulatory_examination_reopened_reauthorized_recovery_investigation.py",
    "backend/app/evaluation/regulatory_examination_reopened_reauthorized_recovery_investigation.py",
    "backend/app/schemas/regulatory_examination_reopened_reauthorized_recovery_investigation.py",
    "backend/app/services/regulatory_examination_reopened_reauthorized_recovery_investigation.py",
    "backend/app/api/v1/regulatory_examination_reopened_reauthorized_recovery_investigation.py",
    "backend/app/workers/regulatory_examination_reopened_reauthorized_recovery_investigation.py",
    "backend/tests/test_regulatory_examination_reopened_reauthorized_recovery_investigation.py",
    "backend/alembic/versions/0086_reg_exam_reopened_reauthorized_recovery_investigation.py",
    "config/policies/regulatory-examination-reopened-reauthorized-recovery-investigation.yaml",
    "sample-data/regulatory/reopened_reauthorized_recovery_investigation_scenarios.json",
    "docs/regulatory-examination-reopened-reauthorized-recovery-investigation.md",
    "artifacts/regulatory-examination/reopened_reauthorized_recovery_investigation_manifest.json",
]
for rel in required:
    if not (ROOT / rel).exists(): raise SystemExit(f"missing {rel}")
main = (ROOT / "backend/app/main.py").read_text()
assert "regulatory_examination_reopened_reauthorized_recovery_investigation_router" in main
cfg = (ROOT / "backend/app/core/config.py").read_text()
assert "regulatory_examination_reopened_reauthorized_recovery_investigation_model_enabled" in cfg
migration = (ROOT / "backend/alembic/versions/0086_reg_exam_reopened_reauthorized_recovery_investigation.py").read_text()
assert 'down_revision = "0085_reg_exam_reclosed_reauthorized_recovery_surveillance"' in migration
domain = (ROOT / "backend/app/domain/regulatory_examination_reopened_reauthorized_recovery_investigation.py").read_text()
assert '"ai_can_authorize_recovery_remediation": False' in domain
assert '"release90_human_reopening_reference_required": True' in domain
print("release91 verification: PASS")
