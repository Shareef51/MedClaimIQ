from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def test_release41_frontend_bff_worker_and_config_contract():
    page=(ROOT/'frontend/app/review/accounting/page.tsx').read_text();api=(ROOT/'frontend/lib/api.ts').read_text();bff=(ROOT/'frontend/app/api/reviewer/[...path]/route.ts').read_text();worker=(ROOT/'backend/app/workers/accounting_reconciliation.py').read_text();values=(ROOT/'infra/helm/medclaimiq/values.yaml').read_text();config=(ROOT/'config/accounting_ledger.yaml').read_text()
    for token in ['ERA/EFT','Immutable journal chain','Accounting periods','human accounting-controller close']:assert token in page
    assert 'accountingLedger' in api and 'reconcileAccountingPayment' in api and 'closeAccountingPeriod' in api
    assert 'accounting-ledger' in bff
    for forbidden in ['_post_journal(', 'approve_adjustment(', 'close_period(', 'authorize_packet(', 'handoff(']:assert forbidden not in worker
    assert 'accounting-reconciliation:' in values and 'automatic_fund_movement: false' in config
