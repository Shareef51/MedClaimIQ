from pathlib import Path
import ast,json,yaml
ROOT=Path(__file__).resolve().parents[1]; MOD="production_go_live_governance_final_release_certification"
required=[f"backend/app/domain/{MOD}.py",f"backend/app/evaluation/{MOD}.py",f"backend/app/schemas/{MOD}.py",f"backend/app/services/{MOD}.py",f"backend/app/api/v1/{MOD}.py",f"backend/app/workers/{MOD}.py",f"backend/tests/test_{MOD}.py","backend/alembic/versions/0105_final_production_go_live.py","config/policies/final-production-go-live.yaml","docs/FINAL_PRODUCTION_GO_LIVE.md","docs/FINAL_PRODUCTION_READINESS_REPORT.md","docs/RECRUITER_DEMO_GUIDE.md","sample-data/operations/final_go_live_scenarios.json","artifacts/release/final_release_manifest.json","artifacts/release/final_production_readiness_report.json","artifacts/release/final_audit_evidence_index.json","schemas/release/final-production-go-live.schema.json",".github/workflows/final-production-go-live.yml","scripts/generate_final_release_evidence.py"]
for x in required:
    if not (ROOT/x).exists(): raise SystemExit(f"missing {x}")
main=(ROOT/'backend/app/main.py').read_text(); assert 'production_go_live_governance_final_release_certification_router' in main
cfg=(ROOT/'backend/app/core/config.py').read_text(); assert 'final_production_go_live_enabled: bool = True' in cfg
mig=(ROOT/'backend/alembic/versions/0105_final_production_go_live.py').read_text(); assert 'down_revision="0104_operational_go_live_readiness_certification"' in mig
policy=yaml.safe_load((ROOT/'config/policies/final-production-go-live.yaml').read_text()); assert policy['human_authority']['automated_production_promotion'] is False
sample=json.loads((ROOT/'sample-data/operations/final_go_live_scenarios.json').read_text()); assert sample['release']==110 and sample['scenario_count']>=15
manifest=json.loads((ROOT/'artifacts/release/final_release_manifest.json').read_text()); assert manifest['final_release'] is True
for x in [r for r in required if r.endswith('.py')]+['backend/app/main.py','backend/app/core/config.py']: ast.parse((ROOT/x).read_text(),filename=x)
print('release110 verification: PASS')
