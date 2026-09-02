from pathlib import Path


required = {
    "backend/app/security/oidc.py": ["OIDCTokenVerifier", "RemoteJWKSProvider", "verify_signature"],
    "backend/app/security/authentication.py": ["resolve_external_identity", "session_required"],
    "backend/app/middleware/authentication.py": ["X-Tenant-Id", "request.state.tenant_id"],
    "backend/app/models/authentication.py": ["AuthenticationSessionModel", "external_session_hash"],
    "backend/alembic/versions/0002_oidc_authentication_sessions.py": [
        "external_issuer",
        "ENABLE ROW LEVEL SECURITY",
        "authentication_sessions_tenant_isolation",
    ],
    "config/authentication_policy.json": ["issuer", "subject", "HMAC-SHA256"],
}

for filename, markers in required.items():
    text = Path(filename).read_text()
    missing = [marker for marker in markers if marker not in text]
    if missing:
        raise SystemExit(f"{filename}: missing {missing}")

print("authentication architecture verification passed")
