from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def test_release_engineering_migration_has_rls_and_immutable_history():
    t=(ROOT/'backend/alembic/versions/0022_release_engineering.py').read_text()
    for table in ['release_manifests','deployment_records','release_gate_results']:
        assert table in t
    assert 'ENABLE ROW LEVEL SECURITY' in t
    assert 'FORCE ROW LEVEL SECURITY' in t
    assert 'medclaimiq_reject_immutable_change' in t
