from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.domain.production_performance_resilience_disaster_recovery_operational_readiness import REQUIRED_OPERATIONAL_GATES
from app.evaluation.production_performance_resilience_disaster_recovery_operational_readiness import operational_go_live_readiness, operational_evidence_pack

def main():
    payload={"release_id":"medclaimiq-rc-109","candidate_version":"v109.0.0-rc1","release107_release_candidate_decision_version_id":"HUMAN-RC-REQUIRED","release108_release_security_certification_version_id":"HUMAN-SECURITY-CERT-REQUIRED","gates":{g:True for g in REQUIRED_OPERATIONAL_GATES},"open_operational_risks":[],"evidence_refs":["performance/k6/api_claims.js","performance/k6/rag_agents_mcp.js","performance/k6/sse_scale.js","infra/dr/backup-restore-matrix.json","infra/dr/dr-objectives.json","chaos/chaos-mesh"],"runbook_refs":["docs/OPERATIONAL_GO_LIVE_READINESS.md","docs/DISASTER_RECOVERY_RUNBOOK.md","docs/INCIDENT_RESPONSE_RUNBOOK.md","docs/RESILIENCE_CHAOS_RUNBOOK.md","docs/RELEASE_ROLLBACK_RUNBOOK.md"],"dashboard_refs":["infra/observability/otel-collector.yaml"],"drill_refs":["sample-data/operations/operational_readiness_scenarios.json"]}
    ready=operational_go_live_readiness(payload); pack=operational_evidence_pack(payload)
    out=ROOT/'artifacts/operations/generated_operational_evidence_pack.json'; out.write_text(json.dumps({"readiness":ready,"evidence_pack":pack,"simulation_only":True,"live_environment_drills_executed":False,"note":"Deterministic contract evidence only; live production-scale load, chaos and DR drills require authorized target environments and human execution."},indent=2,sort_keys=True))
    print(json.dumps({"operational_go_live_ready_for_human_review":ready["operational_go_live_ready"],"evidence_pack_hash":pack["evidence_pack_hash"],"output":str(out.relative_to(ROOT))},indent=2))
if __name__=='__main__': main()
