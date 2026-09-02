from pathlib import Path
import json
import yaml

ROOT = Path(__file__).resolve().parents[1]
required = [
    "backend/app/domain/regulatory_examination_reclosed_reauthorized_enterprise_remediation_surveillance.py",
    "backend/app/evaluation/regulatory_examination_reclosed_reauthorized_enterprise_remediation_surveillance.py",
    "backend/app/schemas/regulatory_examination_reclosed_reauthorized_enterprise_remediation_surveillance.py",
    "backend/app/services/regulatory_examination_reclosed_reauthorized_enterprise_remediation_surveillance.py",
    "backend/app/api/v1/regulatory_examination_reclosed_reauthorized_enterprise_remediation_surveillance.py",
    "backend/app/workers/regulatory_examination_reclosed_reauthorized_enterprise_remediation_surveillance.py",
    "backend/tests/test_regulatory_examination_reclosed_reauthorized_enterprise_remediation_surveillance.py",
    "backend/alembic/versions/0097_reg_exam_reclosed_reauthorized_enterprise_remediation_surveillance.py",
    "config/policies/regulatory-examination-reclosed-reauthorized-enterprise-remediation-surveillance.yaml",
    "sample-data/regulatory/reclosed_reauthorized_enterprise_remediation_surveillance_scenarios.json",
    "docs/regulatory-examination-reclosed-reauthorized-enterprise-remediation-surveillance.md",
    "artifacts/regulatory-examination/reclosed_reauthorized_enterprise_remediation_surveillance_manifest.json",
]
for rel in required:
    if not (ROOT / rel).exists(): raise SystemExit(f"missing {rel}")
main=(ROOT / "backend/app/main.py").read_text()
assert "regulatory_examination_reclosed_reauthorized_enterprise_remediation_surveillance_router" in main
cfg=(ROOT / "backend/app/core/config.py").read_text()
assert "regulatory_examination_reclosed_reauthorized_enterprise_remediation_surveillance_model_enabled" in cfg
migration=(ROOT / "backend/alembic/versions/0097_reg_exam_reclosed_reauthorized_enterprise_remediation_surveillance.py").read_text()
assert 'down_revision = "0096_reg_exam_reauthorized_enterprise_remediation_outcome_validation"' in migration
domain=(ROOT / "backend/app/domain/regulatory_examination_reclosed_reauthorized_enterprise_remediation_surveillance.py").read_text()
assert '"ai_can_reopen_program": False' in domain
assert '"release101_reauthorized_enterprise_remediation_sustainability_reclosure_reference_required": True' in domain
assert '"ai_can_detect_root_cause_treatment_decay": True' in domain
assert '"segregation_of_duties_required": True' in domain
with (ROOT / "config/policies/regulatory-examination-reclosed-reauthorized-enterprise-remediation-surveillance.yaml").open() as fh:
    policy=yaml.safe_load(fh)
assert policy["reopening_governance"]["human_only_reopening"] is True
assert policy["enterprise_escalation"]["independent_reassessment_required"] is True
assert policy["surveillance"]["persistent_emergent_root_cause_treatment_decay_detection"] is True
with (ROOT / "sample-data/regulatory/reclosed_reauthorized_enterprise_remediation_surveillance_scenarios.json").open() as fh:
    scenarios=json.load(fh)
assert len(scenarios["scenarios"]) >= 2 and scenarios["release"] == 102
with (ROOT / "artifacts/regulatory-examination/reclosed_reauthorized_enterprise_remediation_surveillance_manifest.json").open() as fh:
    manifest=json.load(fh)
assert manifest["release"] == 102 and manifest["migration"].startswith("0097_")
print("release102 verification: PASS")
