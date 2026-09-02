from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
required=['backend/app/domain/regulatory_examination_reauthorized_enterprise_remediation_outcome_validation.py', 'backend/app/evaluation/regulatory_examination_reauthorized_enterprise_remediation_outcome_validation.py', 'backend/app/schemas/regulatory_examination_reauthorized_enterprise_remediation_outcome_validation.py', 'backend/app/services/regulatory_examination_reauthorized_enterprise_remediation_outcome_validation.py', 'backend/app/api/v1/regulatory_examination_reauthorized_enterprise_remediation_outcome_validation.py', 'backend/app/workers/regulatory_examination_reauthorized_enterprise_remediation_outcome_validation.py', 'backend/tests/test_regulatory_examination_reauthorized_enterprise_remediation_outcome_validation.py', 'backend/alembic/versions/0096_reg_exam_reauthorized_enterprise_remediation_outcome_validation.py', 'config/policies/regulatory-examination-reauthorized-enterprise-remediation-outcome-validation.yaml', 'sample-data/regulatory/reauthorized_enterprise_remediation_outcome_validation_scenarios.json', 'docs/regulatory-examination-reauthorized-enterprise-remediation-outcome-validation.md']
for rel in required:
    if not (ROOT/rel).exists(): raise SystemExit(f"missing {rel}")
main=(ROOT/"backend/app/main.py").read_text(); assert "regulatory_examination_reauthorized_enterprise_remediation_outcome_validation_router" in main
cfg=(ROOT/"backend/app/core/config.py").read_text(); assert "regulatory_examination_reauthorized_enterprise_remediation_outcome_validation_model_enabled" in cfg
m=(ROOT/"backend/alembic/versions/0096_reg_exam_reauthorized_enterprise_remediation_outcome_validation.py").read_text(); assert 'down_revision = "0095_reg_exam_reauthorized_enterprise_remediation_execution"' in m
d=(ROOT/"backend/app/domain/regulatory_examination_reauthorized_enterprise_remediation_outcome_validation.py").read_text(); assert '"ai_can_accept_residual_systemic_risk": False' in d and '"human_sustainability_reclosure_required": True' in d
json.loads((ROOT/"sample-data/regulatory/reauthorized_enterprise_remediation_outcome_validation_scenarios.json").read_text()); json.loads((ROOT/"artifacts/regulatory-examination/reauthorized_enterprise_remediation_outcome_validation_manifest.json").read_text())
print("release101 verification: PASS")
