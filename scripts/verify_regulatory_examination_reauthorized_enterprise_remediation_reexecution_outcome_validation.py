from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
required=[
"backend/app/domain/regulatory_examination_reauthorized_enterprise_remediation_reexecution_outcome_validation.py",
"backend/app/evaluation/regulatory_examination_reauthorized_enterprise_remediation_reexecution_outcome_validation.py",
"backend/app/schemas/regulatory_examination_reauthorized_enterprise_remediation_reexecution_outcome_validation.py",
"backend/app/services/regulatory_examination_reauthorized_enterprise_remediation_reexecution_outcome_validation.py",
"backend/app/api/v1/regulatory_examination_reauthorized_enterprise_remediation_reexecution_outcome_validation.py",
"backend/app/workers/regulatory_examination_reauthorized_enterprise_remediation_reexecution_outcome_validation.py",
"backend/tests/test_regulatory_examination_reauthorized_enterprise_remediation_reexecution_outcome_validation.py",
"backend/alembic/versions/0100_reg_exam_reauth_enterprise_remed_reexec_outcome_validation.py",
"config/policies/regulatory-examination-reauthorized-enterprise-remediation-reexecution-outcome-validation.yaml",
"sample-data/regulatory/reauthorized_enterprise_remediation_reexecution_outcome_validation_scenarios.json",
"docs/regulatory-examination-reauthorized-enterprise-remediation-reexecution-outcome-validation.md",
"artifacts/regulatory-examination/reauthorized_enterprise_remediation_reexecution_outcome_validation_manifest.json",
]
for rel in required:
    if not (ROOT/rel).exists(): raise SystemExit(f"missing {rel}")
main=(ROOT/"backend/app/main.py").read_text(); assert "regulatory_examination_reauthorized_enterprise_remediation_reexecution_outcome_validation_router" in main
cfg=(ROOT/"backend/app/core/config.py").read_text(); assert "regulatory_examination_reauthorized_enterprise_remediation_reexecution_outcome_validation_model_enabled" in cfg
m=(ROOT/"backend/alembic/versions/0100_reg_exam_reauth_enterprise_remed_reexec_outcome_validation.py").read_text(); assert 'down_revision="0099_reg_exam_reauthorized_enterprise_remediation_reexecution"' in m or 'down_revision = "0099_reg_exam_reauthorized_enterprise_remediation_reexecution"' in m
d=(ROOT/"backend/app/domain/regulatory_examination_reauthorized_enterprise_remediation_reexecution_outcome_validation.py").read_text(); assert '"ai_can_accept_residual_systemic_risk": False' in d and '"human_sustainability_reclosure_required": True' in d and '"release104_enterprise_remediation_reexecution_reference_required": True' in d
json.loads((ROOT/"sample-data/regulatory/reauthorized_enterprise_remediation_reexecution_outcome_validation_scenarios.json").read_text())
manifest=json.loads((ROOT/"artifacts/regulatory-examination/reauthorized_enterprise_remediation_reexecution_outcome_validation_manifest.json").read_text()); assert manifest["release"]==105 and manifest["migration"].startswith("0100_")
print("release105 verification: PASS")
