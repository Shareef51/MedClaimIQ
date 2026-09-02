from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
checks={
 "domain":ROOT/'backend/app/domain/recovery_operations.py',"models":ROOT/'backend/app/models/recovery_operations.py',"service":ROOT/'backend/app/services/recovery_operations.py',"api":ROOT/'backend/app/api/v1/recovery_operations.py',"migration":ROOT/'backend/alembic/versions/0039_recovery_operations_provider_disputes.py',"worker":ROOT/'backend/app/workers/recovery_operations.py',"page":ROOT/'frontend/app/review/recovery-operations/page.tsx',"policy":ROOT/'config/recovery_operations_policy.json',"dataset":ROOT/'data/evaluation/recovery_operations_cases.json'}
missing=[k for k,p in checks.items() if not p.exists()]
if missing:print('missing',missing);sys.exit(1)
domain=checks['domain'].read_text();service=checks['service'].read_text();worker=checks['worker'].read_text();migration=checks['migration'].read_text();page=checks['page'].read_text();policy=json.loads(checks['policy'].read_text());dataset=json.loads(checks['dataset'].read_text())
required=['"ai_can_adjudicate_provider_dispute": False','"ai_can_approve_accounting_change": False','"ai_can_authorize_payment": False','"ai_can_collect_funds": False','"background_worker_can_move_money": False','"independent_human_dispute_resolution_required": True']
assert all(x in domain for x in required)
assert 'direct provider dispute resolution is retired' in service and 'open provider dispute blocks recovery closure' in service
assert (ROOT/'backend/app/services/provider_dispute_resolution.py').exists()
for forbidden in ['resolve_dispute(', 'record_recovery(', 'close_case(', 'approve_adjustment(', 'authorize_packet(', 'handoff(', '_post_journal(']:assert forbidden not in worker
assert 'reject_recovery_immutable_mutation' in migration and migration.count('ENABLE ROW LEVEL SECURITY')>=1 and migration.count('FORCE ROW LEVEL SECURITY')>=1
assert policy['allow_worker_financial_mutation'] is False and policy['allow_ai_dispute_adjudication'] is False and policy['allow_automatic_collection_or_fund_movement'] is False
assert len(dataset)>=5 and all(x.get('requires_human_resolution') is True for x in dataset)
assert 'Recovery & Provider Disputes' in page and 'Authority boundary' in page
print('recovery operations/provider dispute/outcome verification verifier: PASS')
