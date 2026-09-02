from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main() -> None:
    p=json.loads((ROOT/'config/cloud_infrastructure_policy.json').read_text())
    checks={
      'postgres_pitr':p['data']['postgres_pitr_required'],
      'object_versioning':p['data']['object_versioning_required'],
      'multi_az':p['availability']['multi_az_required'],
      'restore_runbook':(ROOT/'docs/DISASTER_RECOVERY_RUNBOOK.md').exists(),
      'immutable_vector_projection':'rebuild' in (ROOT/'docs/DISASTER_RECOVERY_RUNBOOK.md').read_text().lower(),
      'rto_rpo_defined':p['dr_targets']['rto_minutes']>0 and p['dr_targets']['rpo_minutes']>=0,
    }
    failed=[k for k,v in checks.items() if not v]
    report={'decision':'PASS' if not failed else 'BLOCK','checks':checks,'failed':failed,'rto_minutes':p['dr_targets']['rto_minutes'],'rpo_minutes':p['dr_targets']['rpo_minutes']}
    out=ROOT/'artifacts/infrastructure'; out.mkdir(parents=True,exist_ok=True); (out/'restore-readiness.json').write_text(json.dumps(report, indent=2) + '\n')
    if failed: raise SystemExit(f"restore readiness BLOCK: {failed}")
    print('restore readiness: PASS')
if __name__=='__main__': main()
