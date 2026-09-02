from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=["backend/app/domain/regulatory_examination_reopened_recovery_investigation.py","backend/app/evaluation/regulatory_examination_reopened_recovery_investigation.py","backend/app/services/regulatory_examination_reopened_recovery_investigation.py","backend/app/api/v1/regulatory_examination_reopened_recovery_investigation.py","backend/app/workers/regulatory_examination_reopened_recovery_investigation.py","backend/alembic/versions/0078_reg_exam_reopened_recovery_investigation.py","config/policies/regulatory-examination-reopened-recovery-investigation.yaml","docs/regulatory-examination-reopened-recovery-investigation.md"]
missing=[x for x in required if not (ROOT/x).exists()]
assert not missing,missing
main=(ROOT/'backend/app/main.py').read_text(); assert 'regulatory_examination_reopened_recovery_investigation_router' in main
print('release83 verification: PASS')
