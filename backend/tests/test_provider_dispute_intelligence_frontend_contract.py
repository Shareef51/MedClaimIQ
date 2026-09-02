from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"


def test_provider_dispute_intelligence_frontend_bff_sse_worker_and_navigation_contracts():
    page = (FRONTEND / "app/review/provider-disputes/page.tsx").read_text()
    portal = (FRONTEND / "components/portal/provider-dispute-center.tsx").read_text()
    api = (FRONTEND / "lib/api.ts").read_text()
    bff = (FRONTEND / "app/api/reviewer/[...path]/route.ts").read_text()
    portal_bff = (FRONTEND / "app/api/portal/[...path]/route.ts").read_text()
    sse = (BACKEND / "app/api/v1/review_workbench.py").read_text()
    runtime = (BACKEND / "app/workers/production_runtime.py").read_text()
    helm = (ROOT / "infra/helm/medclaimiq/values.yaml").read_text()
    main = (BACKEND / "app/main.py").read_text()

    assert "Provider Dispute Evidence & Policy Review" in page
    assert "Citation drill-down" in page
    assert "Recommendation-only agent" in page
    assert "Provider dispute evidence requests" in portal
    assert "respondProviderDispute" in api
    assert "providerDisputeIntelligenceWorkbench" in api
    assert "provider-dispute-intelligence" in bff
    assert "provider-disputes" in portal_bff
    assert "provider_dispute_intelligence." in sse
    assert "provider-dispute-intelligence" in runtime
    assert "provider-dispute-intelligence:" in helm
    assert "provider_dispute_intelligence_router" in main
