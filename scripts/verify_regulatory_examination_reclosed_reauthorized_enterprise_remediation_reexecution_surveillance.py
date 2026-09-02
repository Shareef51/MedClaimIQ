from pathlib import Path
import json
import yaml

ROOT = Path(__file__).resolve().parents[1]
MOD = "regulatory_examination_reclosed_reauthorized_enterprise_remediation_reexecution_surveillance"
required = [
    f"backend/app/domain/{MOD}.py",
    f"backend/app/evaluation/{MOD}.py",
    f"backend/app/schemas/{MOD}.py",
    f"backend/app/services/{MOD}.py",
    f"backend/app/api/v1/{MOD}.py",
    f"backend/app/workers/{MOD}.py",
    f"backend/tests/test_{MOD}.py",
    "backend/alembic/versions/0101_reg_exam_reclosed_reauth_ent_remed_reexec_surveillance.py",
    "config/policies/regulatory-examination-reclosed-reauthorized-enterprise-remediation-reexecution-surveillance.yaml",
    "sample-data/regulatory/reclosed_reauthorized_enterprise_remediation_reexecution_surveillance_scenarios.json",
    "docs/regulatory-examination-reclosed-reauthorized-enterprise-remediation-reexecution-surveillance.md",
    "artifacts/regulatory-examination/reclosed_reauthorized_enterprise_remediation_reexecution_surveillance_manifest.json",
]
for rel in required:
    if not (ROOT / rel).exists():
        raise SystemExit(f"missing {rel}")
main = (ROOT / "backend/app/main.py").read_text()
assert "regulatory_examination_reclosed_reauthorized_enterprise_remediation_reexecution_surveillance_router" in main
cfg = (ROOT / "backend/app/core/config.py").read_text()
assert "regulatory_examination_reclosed_reauthorized_enterprise_remediation_reexecution_surveillance_model_enabled" in cfg
migration = (ROOT / "backend/alembic/versions/0101_reg_exam_reclosed_reauth_ent_remed_reexec_surveillance.py").read_text()
assert 'down_revision = "0100_reg_exam_reauth_enterprise_remed_reexec_outcome_validation"' in migration
domain = (ROOT / f"backend/app/domain/{MOD}.py").read_text()
assert '"ai_can_reopen_program": False' in domain
assert '"release105_reauthorized_enterprise_remediation_reexecution_sustainability_reclosure_reference_required": True' in domain
assert '"ai_can_detect_root_cause_treatment_decay": True' in domain
assert '"segregation_of_duties_required": True' in domain
service = (ROOT / f"backend/app/services/{MOD}.py").read_text()
assert "def _release105" in service
assert "segregation of duties" in service
with (ROOT / "config/policies/regulatory-examination-reclosed-reauthorized-enterprise-remediation-reexecution-surveillance.yaml").open() as fh:
    policy = yaml.safe_load(fh)
assert policy["reopening_governance"]["human_only_reopening"] is True
assert policy["enterprise_escalation"]["independent_reassessment_required"] is True
assert policy["surveillance"]["persistent_emergent_root_cause_treatment_decay_detection"] is True
assert policy["scope"]["release105_reauthorized_enterprise_remediation_reexecution_sustainability_reclosure_reference_required"] is True
with (ROOT / "sample-data/regulatory/reclosed_reauthorized_enterprise_remediation_reexecution_surveillance_scenarios.json").open() as fh:
    scenarios = json.load(fh)
assert len(scenarios["scenarios"]) >= 2 and scenarios["release"] == 106
with (ROOT / "artifacts/regulatory-examination/reclosed_reauthorized_enterprise_remediation_reexecution_surveillance_manifest.json").open() as fh:
    manifest = json.load(fh)
assert manifest["release"] == 106 and manifest["migration"].startswith("0101_")
print("release106 verification: PASS")
