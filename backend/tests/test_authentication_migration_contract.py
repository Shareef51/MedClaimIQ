from pathlib import Path


def test_authentication_migration_has_identity_and_rls_controls() -> None:
    migration = Path("alembic/versions/0002_oidc_authentication_sessions.py").read_text()
    assert "external_issuer" in migration
    assert "issuer_subject_identity" in migration
    assert "authentication_sessions" in migration
    assert "ENABLE ROW LEVEL SECURITY" in migration
    assert "FORCE ROW LEVEL SECURITY" in migration
    assert "authentication_sessions_tenant_isolation" in migration
    assert "raw_token" not in migration
    assert "refresh_token" not in migration
