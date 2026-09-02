from __future__ import annotations
import json
from pathlib import Path
from starlette.testclient import TestClient
from app.main import app
from app.middleware.rate_limit import InMemorySlidingWindowLimiter
from app.security.data_classification import DLPRedactor,DataClassification
from app.security.audit_integrity import build_hash_chain,verify_hash_chain
from app.security.key_management import AWSKMSDataKeyProvider

ROOT=Path(__file__).resolve().parents[2]

def test_dlp_redacts_phi_and_secrets_without_recording_raw_value():
    safe,findings=DLPRedactor().redact({"patient_name":"Alice Example","authorization":"Bearer secret","note":"email alice@example.com MRN: ABC1234"})
    assert safe["patient_name"]=="[REDACTED_PHI]"; assert safe["authorization"]=="[REDACTED_SECRET]"
    assert "alice@example.com" not in json.dumps(safe); assert any(f.detector=="email" for f in findings)
    assert all(len(f.value_sha256)==64 for f in findings)

def test_hash_chain_detects_tampering():
    secret=b"x"*32; export=build_hash_chain([{"a":1},{"b":2}],signing_secret=secret)
    assert verify_hash_chain(export.lines,expected_root=export.root_sha256,expected_signature=export.signature_hmac_sha256,signing_secret=secret)
    broken=list(export.lines); broken[1]=broken[1].replace('"b":2','"b":3')
    assert not verify_hash_chain(broken,expected_root=export.root_sha256,expected_signature=export.signature_hmac_sha256,signing_secret=secret)

def test_rate_limiter_enforces_window():
    limiter=InMemorySlidingWindowLimiter(); assert limiter.allow("k",limit=2,window_seconds=60,now=1)[0]; assert limiter.allow("k",limit=2,window_seconds=60,now=2)[0]; allowed,retry=limiter.allow("k",limit=2,window_seconds=60,now=3); assert not allowed and retry>0

def test_security_model_is_public_and_does_not_claim_compliance():
    client=TestClient(app); r=client.get('/api/v1/security-model'); assert r.status_code==200; body=r.json(); assert 'HIPAA-ready' in body['compliance_posture']; assert 'certification' in body['compliance_posture']; assert body['dlp']['raw_phi_in_operational_logs'] is False

def test_api_security_headers_present():
    r=TestClient(app).get('/api/v1/security-model'); assert r.headers['x-content-type-options']=='nosniff'; assert r.headers['x-frame-options']=='DENY'; assert "default-src 'none'" in r.headers['content-security-policy']

def test_kms_adapter_never_persists_plaintext_key():
    class Fake:
        def generate_data_key(self,**kw): return {"Plaintext":b"P"*32,"CiphertextBlob":b"cipher","KeyId":"kms-1"}
        def decrypt(self,**kw): return {"Plaintext":b"P"*32}
    provider=AWSKMSDataKeyProvider('kms-1',client=Fake()); plain,enc=provider.generate_data_key(encryption_context={'tenant':'t'}); assert plain==b'P'*32; assert enc.ciphertext_b64!=''; assert 'P'*8 not in enc.ciphertext_b64

def test_security_release_artifacts_exist_and_are_current_generation():
    workflow=(ROOT/'.github/workflows/security-readiness-gate.yml').read_text(); assert 'gitleaks/gitleaks-action@v3' in workflow; assert 'aquasecurity/trivy-action@v0.36.0' in workflow; assert 'anchore/sbom-action@v0.24.0' in workflow; assert 'sigstore/cosign-installer@v4.0.0' in workflow; assert 'attest-build-provenance@v4.1.1' in workflow
    assert (ROOT/'docs/HIPAA_READY_CONTROL_MAPPING.md').exists(); assert (ROOT/'docs/INCIDENT_RESPONSE_RUNBOOK.md').exists(); assert (ROOT/'config/vendor_security_inventory.json').exists()

def test_backend_container_runs_non_root():
    text=(ROOT/'backend/Dockerfile').read_text(); assert 'USER app' in text; assert '--no-server-header' in text

def test_frontend_has_same_origin_and_csp_controls():
    backend=(ROOT/'frontend/lib/server/backend.ts').read_text(); config=(ROOT/'frontend/next.config.ts').read_text(); assert 'Cross-origin mutation rejected' in backend; assert "object-src 'none'" in config; assert 'X-Permitted-Cross-Domain-Policies' in config

def test_security_migration_contract():
    text=(ROOT/'backend/alembic/versions/0021_security_privacy_devsecops.py').read_text();
    for table in ('data_retention_policies','data_disposition_requests','audit_export_manifests','security_readiness_runs','encryption_key_references'): assert table in text
    assert 'FORCE ROW LEVEL SECURITY' in text; assert 'audit_export_manifests","security_readiness_runs' in text
