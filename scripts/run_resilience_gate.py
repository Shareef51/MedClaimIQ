#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--results',default=str(ROOT/'sample-data/resilience_experiments_v1.json')); ap.add_argument('--report-dir',default=str(ROOT/'artifacts/performance')); ap.add_argument('--gate',action='store_true'); args=ap.parse_args()
    data=json.loads(Path(args.results).read_text()); policy=json.loads((ROOT/'config/performance_resilience_policy.json').read_text()); failures=[]; items=[]
    expected_by_dependency={
      'openai':policy['resilience']['openai_failure_fallback'], 'redis':policy['resilience']['redis_failure_fallback'],
      'qdrant':policy['resilience']['rag_vector_store_failure_fallback'], 'kafka':policy['resilience']['kafka_failure_fallback'],
      'postgresql':policy['resilience']['database_failure_fallback'], 'external-mcp-tool':'circuit-open-fast-fail'}
    for e in data['experiments']:
        expected=expected_by_dependency[e['dependency']]
        ok=bool(e['steady_state_before'] and e['steady_state_after'] and e['authorization_boundary_preserved'] and e['data_integrity_preserved'] and e['observed_fallback']==expected)
        if not ok: failures.append(e['name'])
        items.append({**e,'expected_fallback':expected,'passed':ok})
    decision='pass' if not failures else 'block'
    report={'schema_version':'resilience-gate-v1','generated_at':datetime.now(timezone.utc).isoformat(),'decision':decision,'failed_experiments':failures,'results_sha256':hashlib.sha256(Path(args.results).read_bytes()).hexdigest(),'experiments':items}
    out=Path(args.report_dir); out.mkdir(parents=True,exist_ok=True); (out/'resilience-gate.json').write_text(json.dumps(report,indent=2))
    rows=''.join(f"<tr><td>{x['name']}</td><td>{x['dependency']}</td><td>{x['failure_mode']}</td><td>{x['observed_fallback']}</td><td>{'PASS' if x['passed'] else 'FAIL'}</td></tr>" for x in items)
    (out/'resilience-gate.html').write_text(f"<!doctype html><html><body><h1>MedClaimIQ Resilience Gate: {decision.upper()}</h1><table border=1><tr><th>Experiment</th><th>Dependency</th><th>Failure</th><th>Fallback</th><th>Status</th></tr>{rows}</table></body></html>")
    print(f"resilience gate: {decision.upper()} ({len(items)} experiments)")
    return 1 if args.gate and decision!='pass' else 0
if __name__=='__main__': raise SystemExit(main())
