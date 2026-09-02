#!/usr/bin/env python3
"""Environment benchmark runner. Requires explicit endpoints and performs read-only probes only."""
from __future__ import annotations
import argparse, json, statistics, time

def percentile(v,q):
    if not v:return 0.0
    s=sorted(v); return s[max(0,min(len(s)-1,int((len(s)-1)*q)))]
def run(fn,n):
    out=[]
    for _ in range(n):
        t=time.perf_counter(); fn(); out.append((time.perf_counter()-t)*1000)
    return {'samples':n,'p50_ms':round(percentile(out,.5),3),'p95_ms':round(percentile(out,.95),3),'max_ms':round(max(out),3)}
def main():
    p=argparse.ArgumentParser(); p.add_argument('--postgres-url'); p.add_argument('--redis-url'); p.add_argument('--qdrant-url'); p.add_argument('--samples',type=int,default=50); a=p.parse_args(); result={}
    if a.postgres_url:
        import psycopg
        conn=psycopg.connect(a.postgres_url); result['postgres']=run(lambda: conn.execute('SELECT 1').fetchone(),a.samples); conn.close()
    if a.redis_url:
        import redis
        c=redis.Redis.from_url(a.redis_url); result['redis']=run(lambda:c.ping(),a.samples)
    if a.qdrant_url:
        from qdrant_client import QdrantClient
        c=QdrantClient(url=a.qdrant_url); result['qdrant']=run(lambda:c.get_collections(),a.samples)
    if not result: raise SystemExit('provide at least one explicit datastore endpoint')
    print(json.dumps(result,indent=2))
if __name__=='__main__': main()
