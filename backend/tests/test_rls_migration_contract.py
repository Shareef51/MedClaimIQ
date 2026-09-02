from pathlib import Path


def test_initial_migration_contains_postgresql_rls_defense_in_depth() -> None:
    migration = Path("alembic/versions/0001_enterprise_tenancy.py").read_text()

    assert "ENABLE ROW LEVEL SECURITY" in migration
    assert "FORCE ROW LEVEL SECURITY" in migration
    assert "app.current_tenant_id" in migration
    assert "resource_grants_read" in migration
    assert "resource_grants_owner_write" in migration
