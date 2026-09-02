from pathlib import Path
def test_release48_frontend_bff_sse_worker_and_ui_contracts():
    root=Path(__file__).resolve().parents[2];page=(root/'frontend/app/review/recovery-settlement-intelligence/page.tsx').read_text();api=(root/'frontend/lib/api.ts').read_text();bff=(root/'frontend/app/api/reviewer/[...path]/route.ts').read_text();portal_bff=(root/'frontend/app/api/portal/[...path]/route.ts').read_text();portal=(root/'frontend/components/portal/provider-recovery-balance-statements.tsx').read_text();sse=(root/'backend/app/api/v1/review_workbench.py').read_text();runtime=(root/'backend/app/workers/production_runtime.py').read_text();helm=(root/'infra/helm/medclaimiq/values.yaml').read_text()
    assert 'recoverySettlementIntelligencePortfolio' in page and 'Settlement Reconciliation Intelligence' in page and 'Human release to provider portal' in page
    assert 'recoverySettlementIntelligencePortfolio' in api and 'recoveryBalanceStatements' in api
    assert 'recovery-settlement-intelligence' in bff and 'recovery-balance-statements' in portal_bff and 'immutable read-only statements' in portal
    assert 'recovery_settlement_intelligence.' in sse and 'recovery-settlement-intelligence' in runtime and 'recovery-settlement-intelligence:' in helm
