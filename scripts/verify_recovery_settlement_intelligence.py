from pathlib import Path
root=Path(__file__).resolve().parents[1]
checks={
"domain":root/'backend/app/domain/recovery_settlement_intelligence.py',
"service":root/'backend/app/services/recovery_settlement_intelligence.py',
"worker":root/'backend/app/workers/recovery_settlement_intelligence.py',
"migration":root/'backend/alembic/versions/0043_recovery_settlement_reconciliation_intelligence.py',
"ui":root/'frontend/app/review/recovery-settlement-intelligence/page.tsx',
"policy":root/'config/recovery-settlement-intelligence-policy.json',
}
for name,p in checks.items():
    if not p.exists():raise SystemExit(f"missing {name}: {p}")
domain=checks['domain'].read_text();service=checks['service'].read_text();worker=checks['worker'].read_text();migration=checks['migration'].read_text()
for token in ['"ai_can_alter_balances": False','"worker_can_create_bank_transaction": False','"automatic_fund_movement": False','"settlement_and_ledger_citations_required": True']:
    if token not in domain:raise SystemExit(f"missing authority guard {token}")
for forbidden in ['verify_evidence(', '_post_journal(', 'decide_certificate(', 'authorize_packet(', 'handoff(', 'collect_funds(', 'move_money(']:
    if forbidden in worker:raise SystemExit(f"worker authority violation: {forbidden}")
for forbidden in ['_post_journal(', 'decide_certificate(', 'authorize_packet(', 'collect_funds(', 'move_money(']:
    if forbidden in service:raise SystemExit(f"service authority violation: {forbidden}")
if 'down_revision="0042_recovery_settlement_financial_closeout"' not in migration or 'FORCE ROW LEVEL SECURITY' not in migration or 'reject_recovery_settlement_intelligence_mutation' not in migration:raise SystemExit('migration governance incomplete')
print('recovery settlement reconciliation intelligence verifier: PASS')
