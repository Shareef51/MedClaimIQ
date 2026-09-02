from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
required = [
 "backend/app/domain/regulatory_examination_readiness.py",
 "backend/app/schemas/regulatory_examination_readiness.py",
 "backend/app/services/regulatory_examination_readiness.py",
 "backend/app/api/v1/regulatory_examination_readiness.py",
 "backend/app/workers/regulatory_examination_readiness.py",
 "backend/app/evaluation/regulatory_examination_readiness.py",
 "backend/alembic/versions/0060_reg_examination_readiness_operations.py",
 "config/policies/regulatory-examination-readiness.yaml",
 "docs/regulatory/examination-readiness-evidence-rooms.md",
]
missing = [p for p in required if not (ROOT/p).exists()]
if missing: raise SystemExit("Missing Release 65 files: " + ", ".join(missing))
text = (ROOT/"backend/app/domain/regulatory_examination_readiness.py").read_text()
for needle in ["ai_can_transmit_to_regulator\": False", "human_approval_required_for_submission_package\": True"]:
    if needle not in text: raise SystemExit("Authority guard missing: " + needle)
print("Release 65 verification passed")
