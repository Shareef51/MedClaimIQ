#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def require(path, terms):
    text=(ROOT/path).read_text(); missing=[x for x in terms if x not in text]
    if missing: raise SystemExit(f'{path}: missing {missing}')
def main():
    p=json.loads((ROOT/'config/performance_resilience_policy.json').read_text())
    assert p['resilience']['dependency_failure_must_not_bypass_authorization'] is True
    assert p['chaos']['production_execution_requires_explicit_approval'] is True
    assert p['regression']['critical_resilience_failures_allowed']==0
    require('performance/k6/api_claims.js',['ramping-arrival-rate','p(95)<400','rate<0.01'])
    require('performance/k6/rag_agents_mcp.js',['p(95)<1800','p(95)<700'])
    require('performance/k6/sse_scale.js',['ramping-vus','text/event-stream','p(95)<750'])
    require('performance/locust/locustfile.py',['ReviewerJourney','PortalJourney','review.workbench'])
    require('performance/kafka/backlog_stress.py',['recovered','recovery_seconds'])
    require('chaos/chaos-mesh/api-pod-kill.yaml',['PodChaos','pod-kill','medclaimiq-staging'])
    require('chaos/chaos-mesh/kafka-network-partition.yaml',['NetworkChaos','partition','kafka.staging.internal'])
    require('backend/alembic/versions/0023_performance_resilience_engineering.py',['FORCE ROW LEVEL SECURITY','performance_runs','resilience_experiments','_immutable'])
    require('.github/workflows/performance-resilience-gate.yml',['run_performance_gate.py','run_resilience_gate.py','setup-k6-action','locust'])
    print('performance/resilience architecture: PASS')
if __name__=='__main__': main()
