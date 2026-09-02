from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
required=[
"backend/app/domain/regulatory_examination_reauthorized_enterprise_remediation_reexecution.py",
"backend/app/evaluation/regulatory_examination_reauthorized_enterprise_remediation_reexecution.py",
"backend/app/schemas/regulatory_examination_reauthorized_enterprise_remediation_reexecution.py",
"backend/app/services/regulatory_examination_reauthorized_enterprise_remediation_reexecution.py",
"backend/app/api/v1/regulatory_examination_reauthorized_enterprise_remediation_reexecution.py",
"backend/app/workers/regulatory_examination_reauthorized_enterprise_remediation_reexecution.py",
"backend/tests/test_regulatory_examination_reauthorized_enterprise_remediation_reexecution.py",
"backend/alembic/versions/0099_reg_exam_reauthorized_enterprise_remediation_reexecution.py",
"config/policies/regulatory-examination-reauthorized-enterprise-remediation-reexecution.yaml",
"sample-data/regulatory/reauthorized_enterprise_remediation_reexecution_scenarios.json",
"docs/regulatory-examination-reauthorized-enterprise-remediation-reexecution.md",
"artifacts/regulatory-examination/reauthorized_enterprise_remediation_reexecution_manifest.json"]
for rel in required:
    if not (ROOT/rel).exists(): raise SystemExit(f"missing {rel}")
main=(ROOT/"backend/app/main.py").read_text(); assert "regulatory_examination_reauthorized_enterprise_remediation_reexecution_router" in main
cfg=(ROOT/"backend/app/core/config.py").read_text(); assert "regulatory_examination_reauthorized_enterprise_remediation_reexecution_model_enabled" in cfg
m=(ROOT/"backend/alembic/versions/0099_reg_exam_reauthorized_enterprise_remediation_reexecution.py").read_text(); assert 'down_revision="0098_reg_exam_reopened_reauthorized_enterprise_remediation_investigation"' in m
d=(ROOT/"backend/app/domain/regulatory_examination_reauthorized_enterprise_remediation_reexecution.py").read_text(); assert '"ai_can_approve_remediation_execution": False' in d and '"release103_enterprise_remediation_reauthorization_reference_required": True' in d
json.loads((ROOT/"sample-data/regulatory/reauthorized_enterprise_remediation_reexecution_scenarios.json").read_text()); json.loads((ROOT/"artifacts/regulatory-examination/reauthorized_enterprise_remediation_reexecution_manifest.json").read_text())
print("release104 verification: PASS")
