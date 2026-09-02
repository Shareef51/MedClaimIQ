from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=[
 'backend/app/domain/accounting_ledger.py','backend/app/models/accounting_ledger.py','backend/app/repositories/accounting_ledger.py','backend/app/services/accounting_ledger.py','backend/app/api/v1/accounting_ledger.py','backend/app/workers/accounting_reconciliation.py','backend/alembic/versions/0036_accounting_ledger_era_eft_close.py','frontend/app/review/accounting/page.tsx','config/accounting_ledger.yaml','docs/FINANCIAL_LEDGER_ERA_EFT_ACCOUNTING_CLOSE.md','sample-data/accounting-ledger/era_eft_reconciliation.json'
]
missing=[x for x in required if not (ROOT/x).exists()]
assert not missing,missing
domain=(ROOT/'backend/app/domain/accounting_ledger.py').read_text();service=(ROOT/'backend/app/services/accounting_ledger.py').read_text();migration=(ROOT/'backend/alembic/versions/0036_accounting_ledger_era_eft_close.py').read_text();worker=(ROOT/'backend/app/workers/accounting_reconciliation.py').read_text();access=(ROOT/'backend/app/domain/access.py').read_text()
for token in ['"llm_can_post_journal":False','"langgraph_can_post_journal":False','"rag_can_post_journal":False','"mcp_can_post_journal":False','"background_worker_can_post_journal":False','"background_worker_can_close_period":False','"automatic_fund_movement":False','"double_entry_required":True']:assert token in domain,token
for token in ['double-entry journal must be non-zero and exactly balanced','era_total','eft_total','reference_match','returned_payment_reversal','provider_recoupment_receivable','accounting period close blocked','previous_journal_sha256','human accounting controller membership required']:assert token in service,token
assert 'ENABLE ROW LEVEL SECURITY' in migration and 'FORCE ROW LEVEL SECURITY' in migration
assert 'reject_immutable_ledger_journal_mutation' in migration and 'reject_closed_accounting_period_mutation' in migration
assert 'ACCOUNTING_CONTROLLER = "accounting_controller"' in access
for forbidden in ['_post_journal(', 'approve_adjustment(', 'close_period(', 'authorize_packet(', 'handoff(']:assert forbidden not in worker,f'worker authority violation: {forbidden}'
# AI/tool directories must not gain accounting close or finance approval capabilities.
for rel in ['backend/app/agents','backend/app/orchestration','backend/app/rag','backend/app/mcp']:
 d=ROOT/rel
 if d.exists():
  for p in d.rglob('*.py'):
   t=p.read_text(errors='ignore')
   assert '.close_period(' not in t and '.approve_adjustment(' not in t and '.authorize_packet(' not in t,f'unauthorized financial/accounting authority path in {p}'
print('financial ledger ERA/EFT accounting close verifier: PASS')
