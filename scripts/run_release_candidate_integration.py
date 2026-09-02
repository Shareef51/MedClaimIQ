from pathlib import Path
import json, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.evaluation.production_end_to_end_system_integration import assess_golden_journey, release_candidate_readiness
p=json.loads((ROOT/'sample-data/release-candidate/golden_journeys.json').read_text())
journey=assess_golden_journey({**p['golden_journey'],'tenant_id':p['tenant_id']})
readiness=release_candidate_readiness({'gates':p['release_gates'],'quality_scores':p['quality_scores'],'evidence_refs':['artifact:release107-golden-journey'],'release_manifest_ref':'artifacts/release/release_candidate_hardening_manifest.json'})
print(json.dumps({'golden_journey':journey,'release_candidate_readiness':readiness},indent=2))
if not journey['golden_journey_passed'] or not readiness['release_candidate_ready']: sys.exit(1)
