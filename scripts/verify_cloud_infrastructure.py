from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def require(path: str, terms: list[str]) -> None:
    text=(ROOT/path).read_text()
    missing=[x for x in terms if x not in text]
    if missing: raise SystemExit(f"{path}: missing {missing}")

def main() -> None:
    p=json.loads((ROOT/'config/cloud_infrastructure_policy.json').read_text())
    assert p['platform']['kubernetes_minor']=='1.36'
    assert p['availability']['multi_az_required'] is True
    assert p['security']['network_policies_required'] is True
    assert p['data']['postgres_pitr_required'] is True
    assert p['dr_targets']['rto_minutes']>0 and p['dr_targets']['rpo_minutes']>0
    require('infra/helm/medclaimiq/templates/api-deployment.yaml',['topologySpreadConstraints','readinessProbe','livenessProbe','securityContext'])
    require('infra/helm/medclaimiq/templates/hpa.yaml',['HorizontalPodAutoscaler','autoscaling/v2'])
    require('infra/helm/medclaimiq/templates/pdb.yaml',['PodDisruptionBudget'])
    require('infra/helm/medclaimiq/templates/networkpolicy.yaml',['default-deny','NetworkPolicy'])
    require('infra/helm/medclaimiq/templates/migration-job.yaml',['pre-install,pre-upgrade','alembic','upgrade','head'])
    require('infra/helm/medclaimiq/templates/secretproviderclass.yaml',['SecretProviderClass','secrets-store.csi.x-k8s.io'])
    require('infra/terraform/aws/main.tf',['aws_eks_cluster','multi_az                = true','backup_retention_period = 35','aws_wafv2_web_acl','aws_s3_bucket_versioning','aws_iam_openid_connect_provider'])
    require('infra/terraform/azure/main.tf',['azurerm_kubernetes_cluster','ZoneRedundant','geo_redundant_backup_enabled = true','azurerm_web_application_firewall_policy','versioning_enabled  = true','azurerm_federated_identity_credential'])
    require('docs/DISASTER_RECOVERY_RUNBOOK.md',['PostgreSQL','Qdrant','outboxes','actual RTO/RPO'])
    require('.github/workflows/infrastructure-quality-gate.yml',['terraform fmt -check','helm lint','helm template','verify_cloud_infrastructure.py'])
    print('cloud infrastructure architecture: PASS')
if __name__=='__main__': main()
