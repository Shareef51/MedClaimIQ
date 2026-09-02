from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
required=[
"backend/app/domain/regulatory_examination_reopened_enterprise_recovery_investigation.py",
"backend/app/evaluation/regulatory_examination_reopened_enterprise_recovery_investigation.py",
"backend/app/schemas/regulatory_examination_reopened_enterprise_recovery_investigation.py",
"backend/app/services/regulatory_examination_reopened_enterprise_recovery_investigation.py",
"backend/app/api/v1/regulatory_examination_reopened_enterprise_recovery_investigation.py",
"backend/app/workers/regulatory_examination_reopened_enterprise_recovery_investigation.py",
"backend/tests/test_regulatory_examination_reopened_enterprise_recovery_investigation.py",
"backend/alembic/versions/0094_reg_exam_reopened_enterprise_recovery_investigation.py",
"config/policies/regulatory-examination-reopened-enterprise-recovery-investigation.yaml",
"sample-data/regulatory/reopened_enterprise_recovery_investigation_scenarios.json",
"docs/regulatory-examination-reopened-enterprise-recovery-investigation.md",
"artifacts/regulatory-examination/reopened_enterprise_recovery_investigation_manifest.json",
]
for rel in required:
    if not (ROOT/rel).exists(): raise SystemExit(f"missing {rel}")
main=(ROOT/"backend/app/main.py").read_text(); assert "regulatory_examination_reopened_enterprise_recovery_investigation_router" in main
cfg=(ROOT/"backend/app/core/config.py").read_text(); assert "regulatory_examination_reopened_enterprise_recovery_investigation_model_enabled" in cfg
m=(ROOT/"backend/alembic/versions/0094_reg_exam_reopened_enterprise_recovery_investigation.py").read_text(); assert 'down_revision = "0093_reg_exam_reclosed_enterprise_recovery_surveillance"' in m
d=(ROOT/"backend/app/domain/regulatory_examination_reopened_enterprise_recovery_investigation.py").read_text(); assert '"ai_can_authorize_enterprise_remediation": False' in d and '"release98_human_enterprise_reopening_reference_required": True' in d
json.loads((ROOT/"sample-data/regulatory/reopened_enterprise_recovery_investigation_scenarios.json").read_text())
json.loads((ROOT/"artifacts/regulatory-examination/reopened_enterprise_recovery_investigation_manifest.json").read_text())
print("release99 verification: PASS")
