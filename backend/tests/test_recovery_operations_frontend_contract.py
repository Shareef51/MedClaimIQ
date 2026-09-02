from pathlib import Path

def test_release44_reviewer_bff_dashboard_sse_and_worker_contracts():
    root=Path(__file__).resolve().parents[2]
    page=(root/'frontend/app/review/recovery-operations/page.tsx').read_text()
    api=(root/'frontend/lib/api.ts').read_text()
    bff=(root/'frontend/app/api/reviewer/[...path]/route.ts').read_text()
    nav=(root/'frontend/components/review/app-shell.tsx').read_text()
    sse=(root/'backend/app/api/v1/review_workbench.py').read_text()
    runtime=(root/'backend/app/workers/production_runtime.py').read_text()
    helm=(root/'infra/helm/medclaimiq/values.yaml').read_text()
    for token in ['Recovery & Provider Disputes','Provider disputes','Immutable evidence','Authority boundary','recovery.case.created','recovery.dispute.resolved']:assert token in page
    for token in ['recoveryOperationsQueue','recoveryOperationsPortfolio','recoveryOperationsWorkbench','verifyRecoveryOutcome','resolveProviderDispute']:assert token in api
    assert 'recovery-operations' in bff and '/review/recovery-operations' in nav
    assert '"recovery."' in sse
    assert '"recovery-operations"' in runtime and 'run_recovery_operations_all_tenants' in runtime
    assert 'recovery-operations:' in helm

def test_release44_migration_models_policy_and_evaluation_dataset_contract():
    root=Path(__file__).resolve().parents[2]
    migration=(root/'backend/alembic/versions/0039_recovery_operations_provider_disputes.py').read_text()
    models=(root/'backend/app/models/recovery_operations.py').read_text()
    policy=(root/'config/recovery_operations_policy.json').read_text()
    dataset=(root/'data/evaluation/recovery_operations_cases.json').read_text()
    for table in ['recovery_cases','recovery_evidence_packs','recovery_outcomes','provider_disputes','recovery_correspondence','recovery_tasks','recovery_audit_events']:assert table in migration and table in models
    assert 'reject_recovery_immutable_mutation' in migration and 'ENABLE ROW LEVEL SECURITY' in migration and 'FORCE ROW LEVEL SECURITY' in migration
    assert 'allow_automatic_collection_or_fund_movement' in policy and 'false' in policy.lower()
    assert 'requires_human_resolution' in dataset and 'material_provider_dispute' in dataset
