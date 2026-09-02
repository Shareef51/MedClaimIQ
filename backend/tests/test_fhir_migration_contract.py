from pathlib import Path

MIGRATION=Path(__file__).parents[1]/'alembic'/'versions'/'0006_healthcare_fhir.py'


def test_fhir_migration_contains_versioned_evidence_and_rls_contracts():
    text=MIGRATION.read_text()
    for table in ('fhir_connections','fhir_resource_snapshots','fhir_provenance','patient_identity_matches','hospital_cross_verifications','healthcare_events','healthcare_event_outbox'):
        assert table in text
    assert 'ENABLE ROW LEVEL SECURITY' in text
    assert 'FORCE ROW LEVEL SECURITY' in text
    assert 'version_id' in text
    assert 'content_sha256' in text
    assert 'append_only' in text
    assert 'medclaimiq.healthcare.events.v1' in text
