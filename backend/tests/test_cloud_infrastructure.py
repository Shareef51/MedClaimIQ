from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
ROOT=Path(__file__).resolve().parents[2]

def test_cloud_model_is_public_and_describes_ha_dr():
    r=TestClient(app).get('/api/v1/cloud-infrastructure-model')
    assert r.status_code==200
    body=r.json(); assert body['kubernetes_baseline']=='1.36'; assert body['availability']['multi_az'] is True
    assert body['dr_targets']['status']=='architecture-target-not-guarantee'

def test_helm_chart_has_ha_and_security_controls():
    values=(ROOT/'infra/helm/medclaimiq/values.yaml').read_text()
    api=(ROOT/'infra/helm/medclaimiq/templates/api-deployment.yaml').read_text()
    assert 'replicas: 3' in values and 'topologySpreadConstraints' in api
    assert 'readOnlyRootFilesystem: true' in values and 'runAsNonRoot: true' in values

def test_helm_has_pdb_hpa_and_default_deny_network_policy():
    assert 'PodDisruptionBudget' in (ROOT/'infra/helm/medclaimiq/templates/pdb.yaml').read_text()
    assert 'HorizontalPodAutoscaler' in (ROOT/'infra/helm/medclaimiq/templates/hpa.yaml').read_text()
    network=(ROOT/'infra/helm/medclaimiq/templates/networkpolicy.yaml').read_text()
    assert 'default-deny' in network and '169.254.169.254/32' in network

def test_migration_is_pre_upgrade_expand_contract_hook():
    migration=(ROOT/'infra/helm/medclaimiq/templates/migration-job.yaml').read_text()
    assert 'pre-install,pre-upgrade' in migration and '["alembic","upgrade","head"]' in migration
    assert 'expand/contract' in (ROOT/'docs/CLOUD_INFRASTRUCTURE_HA_DR.md').read_text()

def test_secret_store_csi_is_declared():
    spc=(ROOT/'infra/helm/medclaimiq/templates/secretproviderclass.yaml').read_text()
    assert 'secrets-store.csi.x-k8s.io/v1' in spc and 'SecretProviderClass' in spc

def test_aws_module_requires_multi_az_private_data_and_pitr():
    text=(ROOT/'infra/terraform/aws/main.tf').read_text().replace(' ', '')
    assert 'multi_az=true' in text and 'publicly_accessible=false' in text
    assert 'backup_retention_period=35' in text and 'aws_s3_bucket_versioning' in text
    assert 'aws_wafv2_web_acl' in text and 'encryption_config' in text

def test_azure_module_requires_zone_redundancy_private_cluster_and_versioning():
    text=(ROOT/'infra/terraform/azure/main.tf').read_text().replace(' ', '')
    assert 'private_cluster_enabled=true' in text and 'mode="ZoneRedundant"' in text
    assert 'geo_redundant_backup_enabled=true' in text and 'versioning_enabled=true' in text
    assert 'azurerm_web_application_firewall_policy' in text

def test_dr_targets_are_explicitly_targets_not_guarantees():
    import json
    policy=json.loads((ROOT/'config/cloud_infrastructure_policy.json').read_text())
    assert policy['dr_targets']['rto_minutes']==60 and policy['dr_targets']['rpo_minutes']==5
    assert 'targets only' in policy['dr_targets']['note'].lower()

def test_worker_runtime_is_packaged_inside_api_image_module_tree():
    runtime=(ROOT/'backend/app/workers/production_runtime.py').read_text()
    for worker in ['outbox-relay','event-replay','sla-event-scheduler','sla-timer']:
        assert worker in runtime

def test_infrastructure_ci_gate_validates_terraform_helm_and_restore_readiness():
    workflow=(ROOT/'.github/workflows/infrastructure-quality-gate.yml').read_text()
    assert 'terraform validate' in workflow and 'helm lint' in workflow and 'helm template' in workflow
    assert 'verify_restore_readiness.py' in workflow

def test_cloud_workload_identity_is_explicit_for_aws_and_azure():
    aws=(ROOT/'infra/terraform/aws/main.tf').read_text()
    azure=(ROOT/'infra/terraform/azure/main.tf').read_text()
    assert 'aws_iam_openid_connect_provider' in aws and 'sts:AssumeRoleWithWebIdentity' in aws
    assert 'azurerm_federated_identity_credential' in azure and 'api://AzureADTokenExchange' in azure


def test_s3_adapter_supports_short_lived_default_cloud_credentials():
    config=(ROOT/'backend/app/core/config.py').read_text()
    factory=(ROOT/'backend/app/core/ingestion_factory.py').read_text()
    store=(ROOT/'backend/app/storage/object_store.py').read_text()
    assert 's3_use_default_credential_chain' in config
    assert 'settings.s3_use_default_credential_chain' in factory
    assert 'if access_key and secret_key' in store
