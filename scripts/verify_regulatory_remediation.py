from pathlib import Path
root=Path(__file__).resolve().parents[1]
required=[
 'backend/app/domain/regulatory_remediation.py','backend/app/models/regulatory_remediation.py','backend/app/repositories/regulatory_remediation.py','backend/app/services/regulatory_remediation.py','backend/app/api/v1/regulatory_remediation.py','backend/app/workers/regulatory_remediation.py','backend/alembic/versions/0048_regulatory_remediation.py','frontend/app/review/regulatory-remediation/page.tsx','config/regulatory-remediation-policy.json','artifacts/regulatory-remediation/evaluation-dataset.json','docs/architecture/regulatory-remediation-closure-assurance.md'
]
missing=[x for x in required if not (root/x).exists()]
assert not missing,missing
service=(root/'backend/app/services/regulatory_remediation.py').read_text();worker=(root/'backend/app/workers/regulatory_remediation.py').read_text();domain=(root/'backend/app/domain/regulatory_remediation.py').read_text();migration=(root/'backend/alembic/versions/0048_regulatory_remediation.py').read_text();exam=(root/'backend/app/services/regulatory_examination.py').read_text();sse=(root/'backend/app/api/v1/review_workbench.py').read_text()
for token in ['create_plan','approve_plan','complete_task','lock_checkpoint','retest_control','request_waiver','draft_followup','certify_closure','previous_plan_sha256','previous_certification_sha256']:assert token in service,token
for forbidden in ['approve_plan(', 'complete_task(', 'retest_control(', 'certify_closure(', '_post_journal(', 'authorize_packet(', 'collect_funds(', 'move_money(']:assert forbidden not in worker,forbidden
for token in ['"ai_can_approve_remediation": False','"worker_can_close_finding": False','"worker_can_alter_financial_or_accounting_records": False','independent_closure_certification_required']:assert token in domain,token
for token in ['FORCE ROW LEVEL SECURITY','guard_regulatory_remediation_checkpoints_immutable','guard_regulatory_remediation_followups_finalized_immutable','guard_regulatory_remediation_closure_certifications_immutable']:assert token in migration,token
assert 'material examination findings require Release 53 governed corrective-action closure certification' in exam
assert 'regulatory_remediation.' in sse
print('regulatory remediation/corrective-action closure verifier: PASS')
