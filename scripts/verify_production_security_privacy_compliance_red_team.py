from pathlib import Path
import json,yaml,sys
ROOT=Path(__file__).resolve().parents[1]
MOD='production_security_privacy_compliance_red_team'
required=[
 f'backend/app/domain/{MOD}.py',f'backend/app/evaluation/{MOD}.py',f'backend/app/schemas/{MOD}.py',f'backend/app/services/{MOD}.py',f'backend/app/api/v1/{MOD}.py',f'backend/app/workers/{MOD}.py',f'backend/tests/test_{MOD}.py',
 'backend/alembic/versions/0103_release_security_red_team_certification.py','config/policies/release-security-certification.yaml','sample-data/security/adversarial_attack_matrix.json','artifacts/security/release_security_readiness_report.json','artifacts/security/release_security_certification_manifest.json','artifacts/security/compliance_control_map.json','schemas/security/release-security-certification.schema.json','docs/RELEASE_SECURITY_CERTIFICATION.md','SECURITY.md','artifacts/security/local_security_baseline.json','artifacts/security/validation_summary.json','scripts/run_release_security_red_team.py','scripts/scan_repo_security_baseline.py','.github/workflows/release-security-certification.yml']
for rel in required:
    if not (ROOT/rel).exists(): raise SystemExit(f'missing {rel}')
main=(ROOT/'backend/app/main.py').read_text(); assert 'production_security_privacy_compliance_red_team_router' in main
cfg=(ROOT/'backend/app/core/config.py').read_text(); assert 'release_security_certification_enabled' in cfg and 'release_security_critical_findings_allowed: int = 0' in cfg
migration=(ROOT/'backend/alembic/versions/0103_release_security_red_team_certification.py').read_text(); assert 'down_revision="0102_release_candidate_hardening"' in migration
domain=(ROOT/f'backend/app/domain/{MOD}.py').read_text(); assert '"ai_can_issue_security_certification": False' in domain and '"critical_findings_non_waivable": True' in domain
policy=yaml.safe_load((ROOT/'config/policies/release-security-certification.yaml').read_text()); assert policy['release_security_gates']['critical_findings_allowed']==0 and policy['human_authority']['automated_security_certification'] is False
sample=json.loads((ROOT/'sample-data/security/adversarial_attack_matrix.json').read_text()); assert sample['release']==108 and sample['case_count']>=60
manifest=json.loads((ROOT/'artifacts/security/release_security_certification_manifest.json').read_text()); assert manifest['release']==108 and manifest['migration']=='0103_release_security_red_team_certification'
report=json.loads((ROOT/'artifacts/security/release_security_readiness_report.json').read_text()); assert report['human_authority']['release_security_certification_required'] is True and report['automated_production_promotion'] is False
control=json.loads((ROOT/'artifacts/security/compliance_control_map.json').read_text()); assert len(control['controls'])>=10
workflow=(ROOT/'.github/workflows/release-security-certification.yml').read_text(); assert 'Gitleaks' in workflow and 'pip-audit' in workflow and 'Trivy' in workflow and 'CycloneDX' in workflow
print('release108 verification: PASS')
