from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=[
"backend/app/domain/regulatory_examination_reclosed_reauthorized_recovery_surveillance.py",
"backend/app/evaluation/regulatory_examination_reclosed_reauthorized_recovery_surveillance.py",
"backend/app/schemas/regulatory_examination_reclosed_reauthorized_recovery_surveillance.py",
"backend/app/services/regulatory_examination_reclosed_reauthorized_recovery_surveillance.py",
"backend/app/api/v1/regulatory_examination_reclosed_reauthorized_recovery_surveillance.py",
"backend/app/workers/regulatory_examination_reclosed_reauthorized_recovery_surveillance.py",
"backend/tests/test_regulatory_examination_reclosed_reauthorized_recovery_surveillance.py",
"backend/alembic/versions/0085_reg_exam_reclosed_reauthorized_recovery_surveillance.py",
"config/policies/regulatory-examination-reclosed-reauthorized-recovery-surveillance.yaml",
"sample-data/regulatory/reclosed_reauthorized_recovery_surveillance_scenarios.json",
"docs/regulatory-examination-reclosed-reauthorized-recovery-surveillance.md",
"artifacts/regulatory-examination/reclosed_reauthorized_recovery_surveillance_manifest.json"]
for rel in required:
    if not (ROOT/rel).exists(): raise SystemExit(f"missing {rel}")
main=(ROOT/"backend/app/main.py").read_text(); assert "regulatory_examination_reclosed_reauthorized_recovery_surveillance_router" in main
cfg=(ROOT/"backend/app/core/config.py").read_text(); assert "regulatory_examination_reclosed_reauthorized_recovery_surveillance_model_enabled" in cfg
m=(ROOT/"backend/alembic/versions/0085_reg_exam_reclosed_reauthorized_recovery_surveillance.py").read_text(); assert 'down_revision="0084_reg_exam_reauthorized_recovery_outcome_validation"' in m
domain=(ROOT/"backend/app/domain/regulatory_examination_reclosed_reauthorized_recovery_surveillance.py").read_text(); assert '"ai_can_reopen_program": False' in domain
print("release90 verification: PASS")
