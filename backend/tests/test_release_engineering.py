from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
ROOT=Path(__file__).resolve().parents[2]

def test_release_engineering_model_is_public_and_gitops_only():
    r=TestClient(app).get('/api/v1/release-engineering-model')
    assert r.status_code==200
    b=r.json(); assert b['delivery_model']=='gitops-immutable-digest-promotion'
    assert b['gitops']['direct_kubectl_from_release_ci'] is False
    assert b['production_approval']['required'] is True
    assert b['migration_strategy']=='expand-contract'

def test_helm_supports_immutable_digest_references():
    helpers=(ROOT/'infra/helm/medclaimiq/templates/_helpers.tpl').read_text()
    api=(ROOT/'infra/helm/medclaimiq/templates/api-deployment.yaml').read_text()
    assert '$img.digest' in helpers and '@%s' in helpers
    assert 'include "medclaimiq.image"' in api

def test_staging_auto_syncs_but_production_does_not():
    staging=(ROOT/'infra/gitops/argocd/staging-application.yaml').read_text()
    production=(ROOT/'infra/gitops/argocd/production-application.yaml').read_text()
    assert 'automated:' in staging and 'selfHeal: true' in staging
    assert 'automated:' not in production

def test_release_workflow_uses_protected_environments_and_same_digest_promotion():
    w=(ROOT/'.github/workflows/release-promotion.yml').read_text()
    assert 'environment: staging' in w and 'environment: production' in w
    assert 'api_digest' in w and 'frontend_digest' in w and 'cosign verify' in w
    assert 'docker/build-push-action' not in w
    assert 'post_deploy_smoke.py' in w and 'soak_release.py' in w

def test_migration_compatibility_gate_blocks_destructive_upgrade_operations():
    script=(ROOT/'scripts/check_migration_compatibility.py').read_text()
    policy=(ROOT/'config/release_engineering_policy.json').read_text()
    assert 'drop_table' in policy and 'drop_column' in policy and 'upgrade_calls' in script
    assert 'deployed_baseline_example' in policy

def test_progressive_delivery_has_analysis_and_automatic_abort_contract():
    canary=(ROOT/'infra/kubernetes/progressive-delivery/api-canary-rollout.yaml').read_text()
    analysis=(ROOT/'infra/kubernetes/progressive-delivery/analysis-template.yaml').read_text()
    assert all(x in canary for x in ['setWeight: 10','setWeight: 25','setWeight: 50','abortScaleDownDelaySeconds'])
    assert 'http-5xx-ratio' in analysis and 'api-p95-seconds' in analysis and 'failureLimit' in analysis

def test_release_input_paths_are_restricted():
    promote=(ROOT/'scripts/promote_release.py').read_text()
    generate=(ROOT/'scripts/generate_release_manifest.py').read_text()
    assert "manifest_path.parent != release_root" in promote
    assert "unsafe release_id" in generate
