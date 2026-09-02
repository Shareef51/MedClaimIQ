from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
required = [
    "backend/app/domain/regulatory_lessons_learned.py", "backend/app/models/regulatory_lessons_learned.py",
    "backend/app/services/regulatory_lessons_learned.py", "backend/app/api/v1/regulatory_lessons_learned.py",
    "backend/app/evaluation/regulatory_lessons_learned.py", "backend/tests/test_regulatory_lessons_learned.py",
    "backend/alembic/versions/0058_reg_lessons_learned.py", "config/policies/regulatory_lessons_learned.yaml",
    "docs/regulatory/supervisory-lessons-learned-control-improvement.md",
]
missing = [x for x in required if not (ROOT / x).exists()]
assert not missing, f"missing Release 63 assets: {missing}"
text = (ROOT / "backend/app/domain/regulatory_lessons_learned.py").read_text()
for guard in ["ai_can_approve_control_change\": False", "ai_can_modify_policy_or_procedure\": False", "worker_can_collect_or_move_money\": False"]:
    assert guard in text, guard
print("Release 63 verification passed")
