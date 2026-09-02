from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"


def test_provider_dispute_resolution_frontend_bff_sse_and_governance_contracts():
    page = (FRONTEND / "app/review/provider-disputes/page.tsx").read_text()
    api = (FRONTEND / "lib/api.ts").read_text()
    bff = (FRONTEND / "app/api/reviewer/[...path]/route.ts").read_text()
    sse = (BACKEND / "app/api/v1/review_workbench.py").read_text()
    main = (BACKEND / "app/main.py").read_text()
    old_api = (BACKEND / "app/api/v1/recovery_operations.py").read_text()

    assert "Evidence-bound human dispute resolution" in page
    assert "Independent second review" in page
    assert "Final recovery closure" in page
    for token in (
        "providerDisputeResolution",
        "saveProviderDisputeResolutionPacket",
        "secondReviewProviderDisputeResolution",
        "verifyProviderDisputeReconciliation",
        "finalizeProviderDisputeRecovery",
    ):
        assert token in api
    assert "recovery-operations(?:\\/.*)?" in bff
    assert "provider_dispute_resolution." in sse
    assert "provider_dispute_resolution_router" in main
    assert "status_code=410" in old_api
    assert "direct provider dispute resolution retired" in old_api
