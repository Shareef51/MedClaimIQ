from pathlib import Path


def test_multi_rag_migration_has_rls_and_persistence_contracts():
    path = Path(__file__).resolve().parents[1] / "alembic/versions/0008_multi_rag_vector_foundation.py"
    text = path.read_text()
    for table in ("rag_chunks", "rag_index_jobs", "rag_index_records", "rag_index_dead_letters"):
        assert table in text
    assert "ENABLE ROW LEVEL SECURITY" in text
    assert "FORCE ROW LEVEL SECURITY" in text
    assert "idempotency_key" in text
    assert "embedding_dimensions" in text
    assert "rag_index_dead_letters_append_only" in text
