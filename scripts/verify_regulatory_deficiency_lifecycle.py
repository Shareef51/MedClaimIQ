from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=[
"backend/app/domain/regulatory_deficiency_lifecycle.py","backend/app/models/regulatory_deficiency_lifecycle.py",
"backend/app/services/regulatory_deficiency_lifecycle.py","backend/app/api/v1/regulatory_deficiency_lifecycle.py",
"backend/alembic/versions/0054_regulatory_deficiency_lifecycle.py","config/regulatory-deficiency-lifecycle-policy.json",
"docs/regulatory/regulatory-deficiency-lifecycle.md","backend/tests/test_regulatory_deficiency_lifecycle.py"]
missing=[p for p in required if not (ROOT/p).exists()]
assert not missing, f"missing Release 59 assets: {missing}"
print("Release 59 regulatory deficiency lifecycle verification passed")
