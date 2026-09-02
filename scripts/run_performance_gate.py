#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, sys
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

METRIC_MAP = {
    "api_health_p95_ms": ("latency_budgets_ms", "api_health_p95", "lte", "ms"),
    "claim_list_p95_ms": ("latency_budgets_ms", "claim_list_p95", "lte", "ms"),
    "review_workbench_p95_ms": ("latency_budgets_ms", "review_workbench_p95", "lte", "ms"),
    "rag_hybrid_p95_ms": ("latency_budgets_ms", "rag_hybrid_p95", "lte", "ms"),
    "agent_workflow_start_p95_ms": ("latency_budgets_ms", "agent_workflow_start_p95", "lte", "ms"),
    "fhir_read_p95_ms": ("latency_budgets_ms", "fhir_read_p95", "lte", "ms"),
    "mcp_read_p95_ms": ("latency_budgets_ms", "mcp_read_p95", "lte", "ms"),
    "sse_connect_p95_ms": ("latency_budgets_ms", "sse_connect_p95", "lte", "ms"),
    "http_error_rate": ("error_budgets", "http_error_rate_max", "lte", "rate"),
    "rag_error_rate": ("error_budgets", "rag_error_rate_max", "lte", "rate"),
    "agent_start_error_rate": ("error_budgets", "agent_start_error_rate_max", "lte", "rate"),
    "mcp_read_error_rate": ("error_budgets", "mcp_read_error_rate_max", "lte", "rate"),
    "sse_disconnect_rate": ("error_budgets", "sse_disconnect_rate_max", "lte", "rate"),
    "postgres_simple_query_p95_ms": ("datastore_budgets_ms", "postgres_simple_query_p95", "lte", "ms"),
    "redis_roundtrip_p95_ms": ("datastore_budgets_ms", "redis_roundtrip_p95", "lte", "ms"),
    "qdrant_search_p95_ms": ("datastore_budgets_ms", "qdrant_search_p95", "lte", "ms"),
    "worker_events_per_second": ("throughput_targets", "worker_events_per_second", "gte", "events/s"),
    "sse_connections_per_api_replica": ("throughput_targets", "sse_connections_per_api_replica", "gte", "connections"),
}


def sha(data: object) -> str:
    return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()


def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument('--results',default=str(ROOT/'sample-data/performance_results_v1.json')); ap.add_argument('--baseline',default=str(ROOT/'config/performance_baseline_v1.json')); ap.add_argument('--candidate',default='local'); ap.add_argument('--report-dir',default=str(ROOT/'artifacts/performance')); ap.add_argument('--gate',action='store_true'); args=ap.parse_args()
    policy=json.loads((ROOT/'config/performance_resilience_policy.json').read_text())
    results=json.loads(Path(args.results).read_text()); baseline=json.loads(Path(args.baseline).read_text())
    observed=results['metrics']; base=baseline['metrics']; checks=[]; blocked=[]
    for key,(section,budget_key,cmp,unit) in METRIC_MAP.items():
        if key not in observed: blocked.append(f'missing metric: {key}'); continue
        value=float(observed[key]); threshold=float(policy[section][budget_key]); ok=value<=threshold if cmp=='lte' else value>=threshold
        baseline_value=float(base[key]) if key in base else None
        regression=None
        if baseline_value is not None and baseline_value>0:
            regression=(value-baseline_value)/baseline_value
            reg=policy['regression']
            if key.endswith('_p95_ms') and regression>reg['p95_latency_increase_max_fraction']: ok=False
            if cmp=='gte' and -regression>reg['throughput_drop_max_fraction']: ok=False
            if key.endswith('_rate') and value-baseline_value>reg['error_rate_increase_max_absolute']: ok=False
        if not ok: blocked.append(key)
        checks.append({'metric':key,'observed':value,'threshold':threshold,'comparator':cmp,'unit':unit,'baseline':baseline_value,'regression_fraction':regression,'passed':ok})
    decision='pass' if not blocked else 'block'
    report={'schema_version':'performance-gate-v1','candidate':args.candidate,'environment':results.get('environment'),'generated_at':datetime.now(timezone.utc).isoformat(),'decision':decision,'blocked_by':blocked,'policy_sha256':sha(policy),'results_sha256':sha(results),'checks':checks}
    report_dir=Path(args.report_dir); report_dir.mkdir(parents=True,exist_ok=True); (report_dir/'performance-gate.json').write_text(json.dumps(report,indent=2))
    rows=''.join(f"<tr><td>{c['metric']}</td><td>{c['observed']}</td><td>{c['comparator']} {c['threshold']}</td><td>{c['baseline']}</td><td>{'PASS' if c['passed'] else 'FAIL'}</td></tr>" for c in checks)
    (report_dir/'performance-gate.html').write_text(f"<!doctype html><html><body><h1>MedClaimIQ Performance Gate: {decision.upper()}</h1><table border=1><tr><th>Metric</th><th>Observed</th><th>Budget</th><th>Baseline</th><th>Status</th></tr>{rows}</table></body></html>")
    print(f"performance gate: {decision.upper()} ({len(checks)} metrics)")
    return 1 if args.gate and decision!='pass' else 0

if __name__=='__main__': raise SystemExit(main())
