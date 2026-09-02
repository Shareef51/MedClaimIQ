from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def test_performance_migration_forces_rls_and_immutable_history():
    text=(ROOT/'backend/alembic/versions/0023_performance_resilience_engineering.py').read_text()
    for table in ['performance_runs','performance_metrics','resilience_experiments','capacity_snapshots']:
        assert table in text
    assert 'FORCE ROW LEVEL SECURITY' in text
    assert 'medclaimiq_reject_immutable_change' in text
    assert 'down_revision = "0022_release_engineering"' in text


def test_load_and_chaos_artifacts_are_staging_safe():
    workflow=(ROOT/'.github/workflows/performance-resilience-gate.yml').read_text()
    assert 'environment: performance' in workflow
    assert 'environment: chaos-staging' in workflow
    assert "inputs.chaos_experiment != 'none'" in workflow
    for name in ['api-pod-kill.yaml','redis-network-loss.yaml','qdrant-network-delay.yaml','kafka-network-partition.yaml','postgres-network-partition.yaml']:
        text=(ROOT/'chaos/chaos-mesh'/name).read_text()
        assert 'medclaimiq-staging' in text
        assert 'medclaimiq-production' not in text


def test_capacity_and_autoscaling_contract_matches_helm_defaults():
    policy=(ROOT/'config/performance_resilience_policy.json').read_text()
    values=(ROOT/'infra/helm/medclaimiq/values.yaml').read_text()
    assert '"api_cpu_target_percent": 65' in policy
    assert 'cpuUtilization: 65' in values
    assert 'lagThreshold: "100"' in values
