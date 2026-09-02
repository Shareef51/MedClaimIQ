from pathlib import Path
import ast,json,yaml,sys
ROOT=Path(__file__).resolve().parents[1]
MOD='production_performance_resilience_disaster_recovery_operational_readiness'
required=[
 f'backend/app/domain/{MOD}.py',f'backend/app/evaluation/{MOD}.py',f'backend/app/schemas/{MOD}.py',f'backend/app/services/{MOD}.py',f'backend/app/api/v1/{MOD}.py',f'backend/app/workers/{MOD}.py',f'backend/tests/test_{MOD}.py',
 'backend/alembic/versions/0104_operational_go_live_readiness_certification.py','config/policies/operational-go-live-readiness.yaml','sample-data/operations/operational_readiness_scenarios.json','artifacts/operations/operational_go_live_readiness_report.json','artifacts/operations/operational_readiness_manifest.json','artifacts/operations/operational_validation_summary.json','artifacts/operations/drill_matrix.json','artifacts/operations/capacity_forecast_contract.json','schemas/operations/operational-go-live-readiness.schema.json','docs/OPERATIONAL_GO_LIVE_READINESS.md','scripts/run_operational_readiness_drills.py','.github/workflows/operational-go-live-readiness.yml','performance/operational-readiness/load-profile.json','infra/dr/dr-objectives.json']
for rel in required:
    if not (ROOT/rel).exists(): raise SystemExit(f'missing {rel}')
main=(ROOT/'backend/app/main.py').read_text(); assert 'production_performance_resilience_disaster_recovery_operational_readiness_router' in main
cfg=(ROOT/'backend/app/core/config.py').read_text(); assert 'operational_go_live_readiness_enabled: bool = True' in cfg and 'operational_go_live_require_release108_security_certification: bool = True' in cfg
migration=(ROOT/'backend/alembic/versions/0104_operational_go_live_readiness_certification.py').read_text(); assert 'down_revision="0103_release_security_red_team_certification"' in migration
domain=(ROOT/f'backend/app/domain/{MOD}.py').read_text(); assert '"ai_can_issue_operational_certification": False' in domain and '"rpo_rto_breach_non_bypassable": True' in domain
policy=yaml.safe_load((ROOT/'config/policies/operational-go-live-readiness.yaml').read_text()); assert policy['provenance']['release108_human_release_security_certification_required'] is True and policy['human_authority']['automated_operational_certification'] is False
sample=json.loads((ROOT/'sample-data/operations/operational_readiness_scenarios.json').read_text()); assert sample['release']==109 and sample['scenario_count']>=20
manifest=json.loads((ROOT/'artifacts/operations/operational_readiness_manifest.json').read_text()); assert manifest['migration']=='0104_operational_go_live_readiness_certification'
report=json.loads((ROOT/'artifacts/operations/operational_go_live_readiness_report.json').read_text()); assert report['authority']['automated_production_promotion'] is False
workflow=(ROOT/'.github/workflows/operational-go-live-readiness.yml').read_text(); assert 'Operational readiness contract tests' in workflow and 'Chaos and DR manifest contract' in workflow
# Parse all new Python to catch syntax errors without importing optional dependencies.
for rel in [x for x in required if x.endswith('.py')]+['backend/app/main.py','backend/app/core/config.py']:
    ast.parse((ROOT/rel).read_text(),filename=rel)
print('release109 verification: PASS')
