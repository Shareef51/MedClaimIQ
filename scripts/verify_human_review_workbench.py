from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=[
    'backend/app/domain/review_workbench.py','backend/app/models/review_workbench.py',
    'backend/app/repositories/review_workbench.py','backend/app/services/review_workbench.py',
    'backend/app/api/v1/review_workbench.py','backend/alembic/versions/0017_human_review_workbench.py',
    'config/review_workbench_policy.json','docs/HUMAN_REVIEW_WORKBENCH.md'
]
missing=[p for p in required if not (ROOT/p).exists()]
assert not missing, missing
service=(ROOT/'backend/app/services/review_workbench.py').read_text()
for token in ['lock_token_sha256','expected_claim_status_version','override reason is required','EvidencePackModel','HospitalCrossVerificationModel','EvidenceGraphEdgeModel','RAGGuardrailRunModel','MCPApprovalRequestModel','SLATimerModel','enqueue_realtime_event']:
    assert token in service, token
print('human review workbench verification: ok')
