from pathlib import Path
required=[
"backend/app/domain/regulatory_examination_interaction.py","backend/app/services/regulatory_examination_interaction.py","backend/app/api/v1/regulatory_examination_interaction.py","backend/app/schemas/regulatory_examination_interaction.py","backend/app/evaluation/regulatory_examination_interaction.py","backend/app/workers/regulatory_examination_interaction.py","backend/alembic/versions/0062_reg_examination_interaction_governance.py","config/policies/regulatory-examination-interaction.yaml","docs/regulatory-examination-interaction-governance.md"]
root=Path(__file__).resolve().parents[1]
missing=[p for p in required if not (root/p).exists()]
if missing: raise SystemExit(f"missing: {missing}")
print("Release 67 verification passed")
