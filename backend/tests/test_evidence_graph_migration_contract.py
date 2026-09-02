from pathlib import Path


def test_evidence_graph_migration_contains_all_tables_rls_and_immutability():
    migration = Path("alembic/versions/0007_unified_evidence_graph.py").read_text()
    for table in (
        "canonical_entities", "source_entity_mappings", "canonical_code_mappings",
        "claim_line_crosswalks", "evidence_graph_edges", "evidence_contradictions", "rag_metadata_records",
    ):
        assert table in migration
    assert "ENABLE ROW LEVEL SECURITY" in migration
    assert "FORCE ROW LEVEL SECURITY" in migration
    assert "medclaimiq_reject_graph_history_mutation" in migration
    assert "source_entity_mappings" in migration and "append_only" in migration


def test_graph_migration_follows_fhir_migration():
    migration = Path("alembic/versions/0007_unified_evidence_graph.py").read_text()
    assert 'down_revision: str | None = "0006_healthcare_fhir"' in migration
