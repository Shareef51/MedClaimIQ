from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def test_financial_ops_frontend_and_bff_are_wired_to_governed_routes():
    page=(ROOT/"frontend/app/review/financial/page.tsx").read_text()
    api=(ROOT/"frontend/lib/api.ts").read_text()
    bff=(ROOT/"frontend/app/api/reviewer/[...path]/route.ts").read_text()
    shell=(ROOT/"frontend/components/review/app-shell.tsx").read_text()
    assert "Financial Operations & Reconciliation" in page
    assert "Human finance authorize" in page and "LLM authorize funds" in page
    assert "financialHandoff" in api and "authorizeFinancialPacket" in api and "handoffPaymentIntent" in api
    assert "financial-handoff" in bff and "/review/financial" in shell

def test_financial_worker_and_secret_wiring_are_present_without_authorization_power():
    runtime=(ROOT/"backend/app/workers/production_runtime.py").read_text()
    worker=(ROOT/"backend/app/workers/financial_handoff.py").read_text()
    values=(ROOT/"infra/helm/medclaimiq/values.yaml").read_text()
    api=(ROOT/"backend/app/api/v1/financial_handoff.py").read_text()
    main=(ROOT/"backend/app/main.py").read_text()
    assert '"financial-handoff"' in runtime and "run_financial_handoff_all_tenants" in runtime
    assert "ready_for_handoff" in worker and "authorize_packet" not in worker
    assert "financial-handoff:" in values and "financialSettlementWebhookSecretKey" in values
    assert "x-medclaimiq-financial-signature" in api and "hmac.compare_digest" in api
    assert 'financial/webhooks/*' in main
