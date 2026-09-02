from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=[
"backend/app/domain/regulatory_examination_reclosed_supervisory_recovery_surveillance.py",
"backend/app/evaluation/regulatory_examination_reclosed_supervisory_recovery_surveillance.py",
"backend/app/schemas/regulatory_examination_reclosed_supervisory_recovery_surveillance.py",
"backend/app/services/regulatory_examination_reclosed_supervisory_recovery_surveillance.py",
"backend/app/api/v1/regulatory_examination_reclosed_supervisory_recovery_surveillance.py",
"backend/app/workers/regulatory_examination_reclosed_supervisory_recovery_surveillance.py",
"backend/tests/test_regulatory_examination_reclosed_supervisory_recovery_surveillance.py",
"backend/alembic/versions/0089_reg_exam_reclosed_supervisory_recovery_surveillance.py",
"config/policies/regulatory-examination-reclosed-supervisory-recovery-surveillance.yaml",
"sample-data/regulatory/reclosed_supervisory_recovery_surveillance_scenarios.json",
"docs/regulatory-examination-reclosed-supervisory-recovery-surveillance.md",
"artifacts/regulatory-examination/reclosed_supervisory_recovery_surveillance_manifest.json"]
for rel in required:
    if not (ROOT/rel).exists(): raise SystemExit(f"missing {rel}")
main=(ROOT/"backend/app/main.py").read_text(); assert "regulatory_examination_reclosed_supervisory_recovery_surveillance_router" in main
cfg=(ROOT/"backend/app/core/config.py").read_text(); assert "regulatory_examination_reclosed_supervisory_recovery_surveillance_model_enabled" in cfg
m=(ROOT/"backend/alembic/versions/0089_reg_exam_reclosed_supervisory_recovery_surveillance.py").read_text(); assert 'down_revision="0088_reg_exam_supervisory_reauthorized_recovery_outcome_validation"' in m
domain=(ROOT/"backend/app/domain/regulatory_examination_reclosed_supervisory_recovery_surveillance.py").read_text(); assert '"ai_can_reopen_program": False' in domain and '"release93_supervisory_reclosure_reference_required": True' in domain
print("release94 verification: PASS")
