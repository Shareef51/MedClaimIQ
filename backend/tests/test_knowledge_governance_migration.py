from pathlib import Path


def test_knowledge_migration_has_all_governance_tables_rls_and_immutable_history():
    text = Path("alembic/versions/0025_knowledge_lifecycle_governance.py").read_text()
    for table in (
        "knowledge_sources", "knowledge_documents", "knowledge_document_versions", "knowledge_quality_runs",
        "knowledge_reindex_jobs", "knowledge_index_migrations", "knowledge_retrieval_drift_events",
        "knowledge_releases", "knowledge_release_items", "knowledge_governance_events",
    ):
        assert table in text
    assert "ENABLE ROW LEVEL SECURITY" in text
    assert "FORCE ROW LEVEL SECURITY" in text
    assert "medclaimiq_reject_immutable_change" in text
    assert "medclaimiq_guard_knowledge_version_content" in text
    assert "knowledge_document_versions_content_immutable" in text
    assert "medclaimiq_guard_knowledge_release_manifest" in text
    assert "knowledge_releases_manifest_immutable" in text
    assert 'revision = "0025_knowledge_lifecycle_governance"' in text
    assert 'down_revision = "0024_ai_change_management"' in text
