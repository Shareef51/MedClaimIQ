from pathlib import Path
import json, yaml, re, sys
ROOT=Path(__file__).resolve().parents[1]
MOD='production_end_to_end_system_integration'
required=[f'backend/app/domain/{MOD}.py',f'backend/app/evaluation/{MOD}.py',f'backend/app/schemas/{MOD}.py',f'backend/app/services/{MOD}.py',f'backend/app/api/v1/{MOD}.py',f'backend/app/workers/{MOD}.py',f'backend/tests/test_{MOD}.py','backend/alembic/versions/0102_release_candidate_hardening.py','config/policies/release-candidate-hardening.yaml','sample-data/release-candidate/golden_journeys.json','sample-data/release-candidate/failure_injection_matrix.json','artifacts/release/cross_domain_coverage_matrix.json','artifacts/release/production_readiness_report.json','artifacts/release/release_candidate_hardening_manifest.json','schemas/release/release-candidate-readiness.schema.json','docs/release-candidate-hardening.md','scripts/validate_migration_chain.py','scripts/run_release_candidate_integration.py','.github/workflows/release-candidate-hardening.yml']
for rel in required:
    if not (ROOT/rel).exists(): raise SystemExit(f'missing {rel}')
main=(ROOT/'backend/app/main.py').read_text(); assert 'production_end_to_end_system_integration_router' in main
cfg=(ROOT/'backend/app/core/config.py').read_text(); assert 'release_candidate_hardening_enabled' in cfg and 'release_candidate_minimum_quality_score' in cfg
migration=(ROOT/'backend/alembic/versions/0102_release_candidate_hardening.py').read_text(); assert 'down_revision="0101_reg_exam_reclosed_reauth_ent_remed_reexec_surveillance"' in migration
domain=(ROOT/f'backend/app/domain/{MOD}.py').read_text(); assert '"ai_can_declare_release_candidate": False' in domain and '"ai_can_promote_to_production": False' in domain
policy=yaml.safe_load((ROOT/'config/policies/release-candidate-hardening.yaml').read_text()); assert policy['human_authority']['automated_production_promotion'] is False and policy['release_gates']['tenant_isolation_blocking'] is True
sample=json.loads((ROOT/'sample-data/release-candidate/golden_journeys.json').read_text()); assert sample['release']==107 and len(sample['golden_journey']['stages'])==9
manifest=json.loads((ROOT/'artifacts/release/release_candidate_hardening_manifest.json').read_text()); assert manifest['release']==107 and manifest['migration']=='0102_release_candidate_hardening'
workflow=(ROOT/'.github/workflows/release-candidate-hardening.yml').read_text(); assert 'validate_migration_chain.py' in workflow and 'run_release_candidate_integration.py' in workflow
print('release107 verification: PASS')
