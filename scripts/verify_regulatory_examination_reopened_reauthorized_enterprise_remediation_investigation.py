from pathlib import Path
import json
ROOT = Path(__file__).resolve().parents[1]
required = [
    "backend/app/domain/regulatory_examination_reopened_reauthorized_enterprise_remediation_investigation.py",
    "backend/app/evaluation/regulatory_examination_reopened_reauthorized_enterprise_remediation_investigation.py",
    "backend/app/schemas/regulatory_examination_reopened_reauthorized_enterprise_remediation_investigation.py",
    "backend/app/services/regulatory_examination_reopened_reauthorized_enterprise_remediation_investigation.py",
    "backend/app/api/v1/regulatory_examination_reopened_reauthorized_enterprise_remediation_investigation.py",
    "backend/app/workers/regulatory_examination_reopened_reauthorized_enterprise_remediation_investigation.py",
    "backend/tests/test_regulatory_examination_reopened_reauthorized_enterprise_remediation_investigation.py",
    "backend/alembic/versions/0098_reg_exam_reopened_reauthorized_enterprise_remediation_investigation.py",
    "config/policies/regulatory-examination-reopened-reauthorized-enterprise-remediation-investigation.yaml",
    "sample-data/regulatory/reopened_reauthorized_enterprise_remediation_investigation_scenarios.json",
    "docs/regulatory-examination-reopened-reauthorized-enterprise-remediation-investigation.md",
    "artifacts/regulatory-examination/reopened_reauthorized_enterprise_remediation_investigation_manifest.json",
]
for rel in required:
    if not (ROOT / rel).exists(): raise SystemExit(f"missing {rel}")
main = (ROOT / "backend/app/main.py").read_text()
assert "regulatory_examination_reopened_reauthorized_enterprise_remediation_investigation_router" in main
cfg = (ROOT / "backend/app/core/config.py").read_text()
assert "regulatory_examination_reopened_reauthorized_enterprise_remediation_investigation_model_enabled" in cfg
migration = (ROOT / "backend/alembic/versions/0098_reg_exam_reopened_reauthorized_enterprise_remediation_investigation.py").read_text()
assert 'down_revision = "0097_reg_exam_reclosed_reauthorized_enterprise_remediation_surveillance"' in migration
domain = (ROOT / "backend/app/domain/regulatory_examination_reopened_reauthorized_enterprise_remediation_investigation.py").read_text()
assert '"ai_can_authorize_enterprise_remediation": False' in domain
assert '"release102_human_enterprise_reopening_reference_required": True' in domain
json.loads((ROOT / "sample-data/regulatory/reopened_reauthorized_enterprise_remediation_investigation_scenarios.json").read_text())
json.loads((ROOT / "artifacts/regulatory-examination/reopened_reauthorized_enterprise_remediation_investigation_manifest.json").read_text())
print("release103 verification: PASS")
