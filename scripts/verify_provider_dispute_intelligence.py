from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
checks={
 "domain":ROOT/'backend/app/domain/provider_dispute_intelligence.py',"models":ROOT/'backend/app/models/provider_dispute_intelligence.py',"service":ROOT/'backend/app/services/provider_dispute_intelligence.py',"api":ROOT/'backend/app/api/v1/provider_dispute_intelligence.py',"migration":ROOT/'backend/alembic/versions/0040_provider_dispute_intelligence.py',"worker":ROOT/'backend/app/workers/provider_dispute_intelligence.py',"graph":ROOT/'backend/app/orchestration/provider_dispute_intelligence.py',"page":ROOT/'frontend/app/review/provider-disputes/page.tsx',"portal":ROOT/'frontend/components/portal/provider-dispute-center.tsx',"policy":ROOT/'config/provider_dispute_intelligence_policy.json',"dataset":ROOT/'sample-data/evaluation/provider_dispute_intelligence_cases.jsonl'}
missing=[k for k,p in checks.items() if not p.exists()]
if missing:print('missing',missing);sys.exit(1)
domain=checks['domain'].read_text();service=checks['service'].read_text();worker=checks['worker'].read_text();graph=checks['graph'].read_text();migration=checks['migration'].read_text();page=checks['page'].read_text();portal=checks['portal'].read_text();policy=json.loads(checks['policy'].read_text());dataset=[json.loads(x) for x in checks['dataset'].read_text().splitlines() if x.strip()]
required=['"ai_can_adjudicate_dispute": False','"ai_can_change_accounting": False','"ai_can_authorize_payment": False','"ai_can_collect_funds": False','"background_worker_can_move_money": False','"independent_human_resolution_required": True']
assert all(x in domain for x in required)
for forbidden in ['resolve_dispute(', '_post_journal(', 'authorize_packet(', 'handoff(', 'collect_funds(', 'move_money(']:assert forbidden not in service and forbidden not in worker
assert 'background processing requires prior authorized evidence registration' in service
assert 'independent_human_dispute_gate' in graph and '"adjudication_authority":"none"' in graph
assert 'reject_dispute_intelligence_immutable_mutation' in migration and 'FORCE ROW LEVEL SECURITY' in migration
assert policy['allow_ai_dispute_adjudication'] is False and policy['allow_worker_financial_mutation'] is False and policy['allow_automatic_collection_or_fund_movement'] is False
assert len(dataset)>=5 and all(x['requires_human_resolution'] is True for x in dataset)
assert 'Citation drill-down' in page and 'Recommendation-only agent' in page and 'Authority boundary' in page
assert 'independent human' in portal.lower()
print('provider dispute evidence re-ingestion/contract-policy RAG verifier: PASS')
