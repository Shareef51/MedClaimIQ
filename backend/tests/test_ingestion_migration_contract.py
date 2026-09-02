from __future__ import annotations

from pathlib import Path


def test_secure_ingestion_migration_has_rls_versioning_fields_and_immutable_events() -> None:
    migration = (
        Path(__file__).parents[1] / "alembic" / "versions" / "0004_secure_multimodal_ingestion.py"
    ).read_text(encoding="utf-8")

    for table in (
        "evidence_upload_sessions",
        "malware_scans",
        "evidence_processing_events",
        "evidence_event_outbox",
    ):
        assert f'"{table}"' in migration
    assert "ENABLE ROW LEVEL SECURITY" in migration
    assert "FORCE ROW LEVEL SECURITY" in migration
    assert "tenant_isolation" in migration
    assert "storage_version_id" in migration
    assert "storage_etag" in migration
    assert "malware_scans_immutable" in migration
    assert "evidence_processing_events_immutable" in migration
    assert "medclaimiq_reject_immutable_mutation" in migration
