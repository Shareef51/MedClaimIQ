from pathlib import Path


def test_document_intelligence_migration_has_rls_and_append_only_contract() -> None:
    text=(Path(__file__).parents[1]/"alembic/versions/0005_document_intelligence.py").read_text()
    for table in ("document_extraction_runs","extraction_units","extraction_dead_letters"):
        assert table in text
    assert "ENABLE ROW LEVEL SECURITY" in text
    assert "FORCE ROW LEVEL SECURITY" in text
    assert "for table in (\"extraction_units\",\"extraction_dead_letters\")" in text
    assert "_append_only BEFORE UPDATE OR DELETE" in text
    assert "confidence >= 0 AND confidence <= 1" in text
