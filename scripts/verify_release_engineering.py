from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def require(path:str,terms:list[str]):
    text=(ROOT/path).read_text(); missing=[x for x in terms if x not in text]
    if missing: raise SystemExit(f'{path}: missing {missing}')

def main():
    p=json.loads((ROOT/'config/release_engineering_policy.json').read_text())
    assert p['images']['immutable_digest_required'] is True
    assert p['promotion']['production_human_approval_required'] is True
    assert p['gitops']['direct_kubectl_from_release_ci'] is False
    assert p['migrations']['strategy']=='expand-contract'
    require('.github/workflows/release-promotion.yml',['environment: production','cosign verify','post_deploy_smoke.py','soak_release.py','promote_release.py'])
    require('.github/workflows/gitops-drift-detection.yml',['argocd app get','OutOfSync','production'])
    require('.github/workflows/rollback-release.yml',['environment: ${{ inputs.environment }}','promote_release.py'])
    require('infra/gitops/argocd/staging-application.yaml',['automated:','selfHeal: true'])
    prod=(ROOT/'infra/gitops/argocd/production-application.yaml').read_text(); assert 'automated:' not in prod
    require('infra/kubernetes/progressive-delivery/api-canary-rollout.yaml',['setWeight: 10','setWeight: 25','setWeight: 50','abortScaleDownDelaySeconds'])
    require('infra/kubernetes/progressive-delivery/api-bluegreen-rollout.yaml',['autoPromotionEnabled: false','prePromotionAnalysis','postPromotionAnalysis'])
    require('infra/helm/medclaimiq/templates/release-audit-job.yaml',['argocd.argoproj.io/hook: PostSync','app.release.audit','RELEASE_MANIFEST_SHA256'])
    require('backend/alembic/versions/0022_release_engineering.py',['FORCE ROW LEVEL SECURITY','release_manifests','deployment_records','release_gate_results','_immutable'])
    print('release engineering architecture: PASS')
if __name__=='__main__': main()
