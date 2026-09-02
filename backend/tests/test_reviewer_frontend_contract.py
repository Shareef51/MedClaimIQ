from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app

ROOT = Path(__file__).resolve().parents[2]


def test_review_model_exposes_frontend_realtime_contract():
    body = TestClient(app).get('/api/v1/review-model').json()
    assert body['frontend']['queue_sse'] == '/api/v1/review/queue/events'
    assert body['frontend']['browser_bearer_storage'] is False
    assert body['frontend']['human_decision_only'] is True


def test_frontend_has_secure_bff_and_reviewer_surfaces():
    required = [
        'frontend/app/review/page.tsx',
        'frontend/app/review/claims/[claimId]/page.tsx',
        'frontend/components/review/review-queue.tsx',
        'frontend/components/review/claim-workbench.tsx',
        'frontend/lib/server/session.ts',
        'frontend/app/api/reviewer/[...path]/route.ts',
        'frontend/app/api/reviewer/queue/events/route.ts',
        'frontend/app/api/reviewer/claims/[claimId]/events/route.ts',
    ]
    assert not [path for path in required if not (ROOT / path).exists()]
    session = (ROOT / 'frontend/lib/server/session.ts').read_text()
    bff = (ROOT / 'frontend/app/api/reviewer/[...path]/route.ts').read_text()
    workbench = (ROOT / 'frontend/components/review/claim-workbench.tsx').read_text()
    assert 'httpOnly: true' in session
    assert 'localStorage' not in session and 'sessionStorage' not in session
    assert 'assertSameOrigin' in bff and 'ALLOWED' in bff
    assert 'AI override reason required' in workbench
    assert 'Record human decision' in workbench


def test_reviewer_queue_sse_is_tenant_scoped_metadata_stream():
    api = (ROOT / 'backend/app/api/v1/review_workbench.py').read_text()
    stream = (ROOT / 'backend/app/realtime/streaming.py').read_text()
    repo = (ROOT / 'backend/app/repositories/realtime.py').read_text()
    assert '@router.get("/review/queue/events")' in api
    assert 'identity.principal.tenant_id' in api
    assert 'event_prefixes=("review.", "sla.timer.", "sla.post_decision.", "rag.guardrail.", "agent.workflow.", "appeal.", "communication.", "financial_investigation.", "recovery.", "provider_dispute_intelligence.", "provider_dispute_resolution.", "recovery_settlement.", "recovery_settlement_intelligence.", "recovery_control_assurance.", "regulatory_transport.", "regulatory_supervision.", "regulatory_examination.", "regulatory_remediation.", "regulatory_portfolio.")' in api
    assert 'class TenantRealtimeStreamer' in stream
    assert 'tenant_events_after' in repo
