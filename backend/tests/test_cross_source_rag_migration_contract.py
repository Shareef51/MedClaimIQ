from pathlib import Path


def test_cross_source_migration_has_rls_and_immutable_evidence_pack_controls():
    text = Path("alembic/versions/0010_cross_source_evidence_fusion.py").read_text()
    for table in ("rag_evidence_packs", "rag_evidence_pack_items", "rag_evidence_pack_contradictions"):
        assert table in text
    assert "ENABLE ROW LEVEL SECURITY" in text
    assert "FORCE ROW LEVEL SECURITY" in text
    assert "immutable evidence pack snapshot" in text
    assert "append_only" in text
