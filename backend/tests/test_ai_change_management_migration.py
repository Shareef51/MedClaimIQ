from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
MIGRATION=ROOT/"backend/alembic/versions/0024_ai_change_management.py"

def test_ai_change_management_migration_chain_and_rls():
    text=MIGRATION.read_text()
    assert 'down_revision = "0023_performance_resilience_engineering"' in text
    assert "FORCE ROW LEVEL SECURITY" in text
    for table in (
        "ai_configuration_snapshots","ai_environment_assignments","ai_configuration_promotions",
        "ai_experiments","ai_experiment_assignments","ai_experiment_observations",
        "ai_configuration_drift_events","ai_change_events",
    ):
        assert table in text


def test_immutable_governance_histories_have_db_triggers():
    text=MIGRATION.read_text()
    assert "IMMUTABLE = (" in text
    assert "{table}_immutable" in text
    for table in ("ai_configuration_snapshots","ai_experiment_assignments","ai_experiment_observations","ai_configuration_drift_events","ai_change_events"):
        assert table in text
