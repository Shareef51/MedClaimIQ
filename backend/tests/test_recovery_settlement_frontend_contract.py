from pathlib import Path
def test_recovery_settlement_frontend_portal_sse_and_worker_runtime_contracts():
    root=Path(__file__).resolve().parents[2];page=(root/'frontend/app/review/recovery-settlements/page.tsx').read_text();portal=(root/'frontend/components/portal/recovery-settlement-center.tsx').read_text();api=(root/'frontend/lib/api.ts').read_text();stream=(root/'backend/app/api/v1/review_workbench.py').read_text();runtime=(root/'backend/app/workers/production_runtime.py').read_text();helm=(root/'infra/helm/medclaimiq/values.yaml').read_text();main=(root/'backend/app/main.py').read_text()
    assert 'recoverySettlementQueue' in page and 'recovery_settlement.certificate.decided' in page and 'recovery_settlement.' in stream
    assert 'submitRecoverySettlementEvidence' in portal and 'recoverySettlements' in api and 'recovery-settlement' in runtime and 'recovery-settlement: {enabled: true' in helm and 'recovery_settlement_router' in main
