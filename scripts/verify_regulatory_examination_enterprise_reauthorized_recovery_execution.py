from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
required=[
"backend/app/domain/regulatory_examination_enterprise_reauthorized_recovery_execution.py",
"backend/app/evaluation/regulatory_examination_enterprise_reauthorized_recovery_execution.py",
"backend/app/schemas/regulatory_examination_enterprise_reauthorized_recovery_execution.py",
"backend/app/services/regulatory_examination_enterprise_reauthorized_recovery_execution.py",
"backend/app/api/v1/regulatory_examination_enterprise_reauthorized_recovery_execution.py",
"backend/app/workers/regulatory_examination_enterprise_reauthorized_recovery_execution.py",
"backend/tests/test_regulatory_examination_enterprise_reauthorized_recovery_execution.py",
"backend/alembic/versions/0091_reg_exam_enterprise_reauthorized_recovery_execution.py",
"config/policies/regulatory-examination-enterprise-reauthorized-recovery-execution.yaml",
"sample-data/regulatory/enterprise_reauthorized_recovery_execution_scenarios.json",
"docs/regulatory-examination-enterprise-reauthorized-recovery-execution.md",
"artifacts/regulatory-examination/enterprise_reauthorized_recovery_execution_manifest.json",
]
for rel in required:
    if not (ROOT/rel).exists(): raise SystemExit(f"missing {rel}")
main=(ROOT/"backend/app/main.py").read_text(); assert "regulatory_examination_enterprise_reauthorized_recovery_execution_router" in main
cfg=(ROOT/"backend/app/core/config.py").read_text(); assert "regulatory_examination_enterprise_reauthorized_recovery_execution_model_enabled" in cfg
m=(ROOT/"backend/alembic/versions/0091_reg_exam_enterprise_reauthorized_recovery_execution.py").read_text(); assert 'down_revision = "0090_reg_exam_reopened_supervisory_recovery_investigation"' in m
d=(ROOT/"backend/app/domain/regulatory_examination_enterprise_reauthorized_recovery_execution.py").read_text(); assert '"ai_can_approve_control_retransformation": False' in d and '"release95_enterprise_reauthorization_reference_required": True' in d
json.loads((ROOT/"sample-data/regulatory/enterprise_reauthorized_recovery_execution_scenarios.json").read_text())
json.loads((ROOT/"artifacts/regulatory-examination/enterprise_reauthorized_recovery_execution_manifest.json").read_text())
print("release96 verification: PASS")
