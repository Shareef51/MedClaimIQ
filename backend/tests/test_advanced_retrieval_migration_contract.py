from pathlib import Path


def test_advanced_retrieval_migration_has_rls_append_only_telemetry():
    path = Path(__file__).resolve().parents[1] / "alembic/versions/0009_advanced_hybrid_retrieval.py"
    text = path.read_text()
    for table in ("rag_retrieval_runs", "rag_retrieval_candidates"):
        assert table in text
    assert "ENABLE ROW LEVEL SECURITY" in text
    assert "FORCE ROW LEVEL SECURITY" in text
    assert "append-only retrieval telemetry" in text
    assert "query_sha256" in text
    assert "raw_query" not in text
