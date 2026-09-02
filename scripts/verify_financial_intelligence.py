from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=['backend/app/domain/financial_intelligence.py','backend/app/models/financial_intelligence.py','backend/app/repositories/financial_intelligence.py','backend/app/services/financial_intelligence.py','backend/app/api/v1/financial_intelligence.py','backend/app/evaluation/financial_intelligence.py','backend/app/workers/financial_intelligence.py','backend/alembic/versions/0037_financial_intelligence_read_model.py','frontend/app/review/financial-intelligence/page.tsx','config/financial_intelligence.yaml','docs/FINANCIAL_ANALYTICS_RESERVE_PAYMENT_INTEGRITY.md','data/evaluation/financial_intelligence_cases.json','sample-data/financial-intelligence/financial_intelligence_scenario.json']
missing=[x for x in required if not (ROOT/x).exists()];assert not missing,missing
domain=(ROOT/'backend/app/domain/financial_intelligence.py').read_text();service=(ROOT/'backend/app/services/financial_intelligence.py').read_text();worker=(ROOT/'backend/app/workers/financial_intelligence.py').read_text();migration=(ROOT/'backend/alembic/versions/0037_financial_intelligence_read_model.py').read_text();runtime=(ROOT/'backend/app/workers/production_runtime.py').read_text();values=(ROOT/'infra/helm/medclaimiq/values.yaml').read_text()
for token in ['"read_only_source_systems": True','"llm_can_modify_ledger": False','"langgraph_can_modify_ledger": False','"rag_can_modify_ledger": False','"mcp_can_modify_ledger": False','"analytics_worker_can_modify_ledger": False','"ai_can_modify_reserve": False','"ai_can_authorize_payment": False','"ai_can_close_accounting_period": False','"automatic_fund_movement": False','"ledger_citations_required": True']:assert token in domain,token
for token in ['outstanding_reserve','paid_to_incurred_ratio','financial_leakage_exposure','duplicate_payment_groups','reconciliation_anomaly_score','provider_patterns','recoupment_aging','accounting_control_exceptions','period_close_readiness','structured_ledger_hybrid_lexical_citation_retrieval_v1','FinancialCopilotSynthesis','fund_movement_authority="none"']:assert token in service,token
for forbidden in ['_post_journal(','.close_period(','.authorize_packet(','.approve_adjustment(','.handoff(','.request_adjustment(']:assert forbidden not in worker,f'analytics worker authority violation: {forbidden}'
assert 'ENABLE ROW LEVEL SECURITY' in migration and 'FORCE ROW LEVEL SECURITY' in migration and 'reject_financial_intelligence_snapshot_mutation' in migration
assert 'financial-intelligence' in runtime and 'financial-intelligence:' in values
for rel in ['backend/app/agents','backend/app/orchestration','backend/app/rag','backend/app/mcp']:
 d=ROOT/rel
 if d.exists():
  for p in d.rglob('*.py'):
   t=p.read_text(errors='ignore')
   assert 'FinancialIntelligenceService' not in t or 'read_only' in t.lower(),f'financial intelligence authority unexpectedly introduced in {p}'
print('financial analytics reserve/payment integrity/control intelligence verifier: PASS')
