from pathlib import Path


MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "0003_claim_evidence_domain.py"
).read_text()


def test_claim_domain_migration_has_rls_for_every_tenant_table() -> None:
    for table in (
        "patients",
        "providers",
        "policies",
        "encounters",
        "claims",
        "claim_lines",
        "evidence_artifacts",
        "evidence_lineage",
        "claim_status_events",
        "human_review_decisions",
        "audit_events",
    ):
        assert table in MIGRATION
    assert "ENABLE ROW LEVEL SECURITY" in MIGRATION
    assert "FORCE ROW LEVEL SECURITY" in MIGRATION
    assert "app.current_tenant_id" in MIGRATION


def test_provenance_and_decision_records_are_database_immutable() -> None:
    assert "medclaimiq_reject_immutable_mutation" in MIGRATION
    for table in (
        "evidence_lineage",
        "claim_status_events",
        "human_review_decisions",
        "audit_events",
    ):
        assert f"{table}_immutable" in MIGRATION
        assert "BEFORE UPDATE OR DELETE" in MIGRATION
