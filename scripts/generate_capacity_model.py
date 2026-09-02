#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, math
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--api-replicas',type=int,default=3); ap.add_argument('--worker-replicas',type=int,default=3); ap.add_argument('--headroom',type=float,default=.30); ap.add_argument('--output',default=str(ROOT/'artifacts/performance/capacity-model.json')); a=ap.parse_args()
    if not 0.1<=a.headroom<=0.6: raise SystemExit('headroom must be 0.1..0.6')
    p=json.loads((ROOT/'config/performance_resilience_policy.json').read_text()); t=p['throughput_targets']; usable=1-a.headroom
    api_sse=int(a.api_replicas*t['sse_connections_per_api_replica']*usable)
    worker_eps=round(a.worker_replicas*t['worker_events_per_second']*usable,2)
    # Conservative API RPS assumption is benchmark-derived and explicit, not a cloud guarantee.
    per_api_rps=50.0; sustained=round(a.api_replicas*per_api_rps*usable,2)
    model={'schema_version':'capacity-model-v1','generated_at':datetime.now(timezone.utc).isoformat(),'model_version':'capacity-v1','inputs':{'api_replicas':a.api_replicas,'worker_replicas':a.worker_replicas,'headroom_fraction':a.headroom,'assumed_api_rps_per_replica':per_api_rps},'capacity':{'sustained_api_rps':sustained,'sse_connections':api_sse,'worker_events_per_second':worker_eps,'estimated_reviewer_users_at_0.2_rps_each':math.floor(sustained/0.2)},'notes':['capacity values are planning estimates derived from checked-in benchmark assumptions','production sizing requires environment-specific load tests and observed saturation curves']}
    model['assumptions_sha256']=hashlib.sha256(json.dumps(model['inputs'],sort_keys=True).encode()).hexdigest(); out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(model,indent=2)); print(out)
if __name__=='__main__': main()
