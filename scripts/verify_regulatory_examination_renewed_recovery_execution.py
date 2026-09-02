from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=[
"backend/app/domain/regulatory_examination_renewed_recovery_execution.py",
"backend/app/evaluation/regulatory_examination_renewed_recovery_execution.py",
"backend/app/schemas/regulatory_examination_renewed_recovery_execution.py",
"backend/app/services/regulatory_examination_renewed_recovery_execution.py",
"backend/app/api/v1/regulatory_examination_renewed_recovery_execution.py",
"backend/app/workers/regulatory_examination_renewed_recovery_execution.py",
"backend/tests/test_regulatory_examination_renewed_recovery_execution.py",
"backend/alembic/versions/0079_reg_exam_renewed_recovery_execution.py",
"config/policies/regulatory-examination-renewed-recovery-execution.yaml",
"sample-data/regulatory/renewed_recovery_execution_scenarios.json",
"docs/regulatory-examination-renewed-recovery-execution.md",
]
for x in required:
 p=ROOT/x
 if not p.exists(): raise SystemExit(f"missing {x}")
main=(ROOT/"backend/app/main.py").read_text()
assert "regulatory_examination_renewed_recovery_execution_router" in main
cfg=(ROOT/"backend/app/core/config.py").read_text()
assert "regulatory_examination_renewed_recovery_execution_model_enabled" in cfg
print("release84 verification: PASS")
