from pathlib import Path
root=Path(__file__).resolve().parents[1]
required=["backend/app/domain/regulatory_examination_reclosed_recovery_sustainability.py","backend/app/evaluation/regulatory_examination_reclosed_recovery_sustainability.py","backend/app/schemas/regulatory_examination_reclosed_recovery_sustainability.py","backend/app/services/regulatory_examination_reclosed_recovery_sustainability.py","backend/app/api/v1/regulatory_examination_reclosed_recovery_sustainability.py","backend/app/workers/regulatory_examination_reclosed_recovery_sustainability.py","backend/alembic/versions/0081_reg_exam_reclosed_recovery_sustainability.py","backend/tests/test_regulatory_examination_reclosed_recovery_sustainability.py","config/policies/regulatory-examination-reclosed-recovery-sustainability.yaml","docs/regulatory-examination-reclosed-recovery-sustainability-monitoring.md"]
missing=[x for x in required if not (root/x).exists()]
assert not missing,missing
main=(root/"backend/app/main.py").read_text(); assert "regulatory_examination_reclosed_recovery_sustainability_router" in main
config=(root/"backend/app/core/config.py").read_text(); assert "regulatory_examination_reclosed_recovery_sustainability_model_enabled" in config
print("release86 verification: PASS")
