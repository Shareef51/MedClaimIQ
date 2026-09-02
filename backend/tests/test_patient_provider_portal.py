from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.domain.access import Principal, UserRole
from app.realtime.streaming import PortalClaimRealtimeStreamer
from app.services.portal import PortalAccessError, PortalService, SAFE_STATUS_LABELS

ROOT=Path(__file__).resolve().parents[2]

def test_portal_model_is_public_and_minimized():
    r=TestClient(app).get('/api/v1/portal-model')
    assert r.status_code==200
    body=r.json()
    assert set(body['allowed_roles'])=={'patient','provider','hospital_admin'}
    assert 'fraud/waste signals' in body['hidden_internal_sections']
    assert 'quarantine' in body['upload_rule']

def test_portal_claim_endpoint_is_authenticated():
    r=TestClient(app).get('/api/v1/portal/claims')
    assert r.status_code==401

def test_portal_stream_blocks_internal_event_classes():
    safe=PortalClaimRealtimeStreamer._safe
    # call unbound through lightweight object-independent method shape
    obj=PortalClaimRealtimeStreamer.__new__(PortalClaimRealtimeStreamer)
    assert safe(obj,'claim.status_changed')
    assert safe(obj,'portal.document_upload.received')
    assert not safe(obj,'agent.workflow.completed')
    assert not safe(obj,'rag.guardrail.escalated')
    assert not safe(obj,'review.note.added')
    assert not safe(obj,'mcp.tool.completed')

def test_safe_status_labels_are_external_language():
    assert SAFE_STATUS_LABELS['ai_reviewed']=='Review in progress'
    assert SAFE_STATUS_LABELS['pending_evidence']=='More information needed'

def test_internal_reviewer_role_is_rejected_by_portal_service():
    svc=PortalService.__new__(PortalService)
    p=Principal(user_id='usr-reviewer',tenant_id='tenant-a',role=UserRole.CLAIMS_REVIEWER)
    try: svc.require_external_role(p)
    except PortalAccessError: pass
    else: raise AssertionError('reviewer must not be accepted by external portal role gate')

def test_portal_migration_has_rls_and_audit_immutability():
    text=(ROOT/'backend/alembic/versions/0018_patient_provider_portal.py').read_text()
    for table in ('portal_document_requests','portal_submissions','portal_action_events'):
        assert table in text
    assert 'ENABLE ROW LEVEL SECURITY' in text
    assert 'FORCE ROW LEVEL SECURITY' in text
    assert 'portal_action_events_immutable' in text

def test_reviewer_request_more_evidence_creates_portal_request():
    text=(ROOT/'backend/app/services/review_workbench.py').read_text()
    assert 'PortalDocumentRequestModel' in text
    assert 'requested_document_types=requested_document_types' in text
    assert 'status="open"' in text

def test_portal_backend_never_composes_internal_agent_models():
    text=(ROOT/'backend/app/services/portal.py').read_text()
    forbidden=('AgentFindingModel','RAGGuardrailRunModel','ReviewerNoteModel','EvidenceContradictionModel','MCPApprovalRequestModel')
    for name in forbidden: assert name not in text

def test_frontend_portal_has_separate_bff_allowlist_and_no_token_storage():
    proxy=(ROOT/'frontend/app/api/portal/[...path]/route.ts').read_text()
    detail=(ROOT/'frontend/components/portal/claim-detail.tsx').read_text()
    assert 'portal_route_not_allowed' in proxy
    assert 'localStorage' not in proxy+detail
    assert 'sessionStorage' not in proxy+detail
    assert '/review/workbench' not in proxy

def test_frontend_upload_uses_signed_target_and_acknowledgement():
    text=(ROOT/'frontend/components/portal/claim-detail.tsx').read_text()
    assert 'uploadToSignedTarget' in text
    assert 'completeUpload' in text
    assert 'acknowledgement_code' in text
    assert 'EventSource' in text

def test_browser_upload_has_public_presign_endpoint_and_minio_cors():
    compose=(ROOT/'docker-compose.yml').read_text()
    cors=(ROOT/'config/minio-cors.xml').read_text()
    factory=(ROOT/'backend/app/core/ingestion_factory.py').read_text()
    assert 'S3_PUBLIC_ENDPOINT_URL' in compose
    assert 'mc cors set' in compose
    assert 'http://localhost:3000' in cors
    assert 'public_endpoint_url=settings.s3_public_endpoint_url' in factory

def test_missing_document_timer_is_completed_only_after_secure_worker_acceptance():
    worker=(ROOT/'backend/app/workers/evidence_ingestion.py').read_text()
    review=(ROOT/'backend/app/services/review_workbench.py').read_text()
    assert 'claim.missing_evidence.requested' in review
    assert 'claim.missing_evidence.received' in worker
    assert '_sync_portal_submission(upload, accepted=True)' in worker
