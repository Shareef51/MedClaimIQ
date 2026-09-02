#!/usr/bin/env python3
from __future__ import annotations
import argparse,time,urllib.request

def healthy(url):
    try:
        with urllib.request.urlopen(url,timeout=10) as r: return r.status==200
    except Exception: return False

def main():
    p=argparse.ArgumentParser(); p.add_argument('--base-url',required=True); p.add_argument('--minutes',type=int,default=30); p.add_argument('--interval-seconds',type=int,default=30); p.add_argument('--max-failure-rate',type=float,default=0.02); a=p.parse_args()
    deadline=time.monotonic()+a.minutes*60; total=failed=0; url=a.base_url.rstrip('/')+'/api/v1/health'
    while time.monotonic()<deadline:
        total+=1; failed+=0 if healthy(url) else 1; time.sleep(a.interval_seconds)
    rate=failed/max(total,1); print(f'soak probes={total} failed={failed} failure_rate={rate:.4f}'); return 0 if rate<=a.max_failure_rate else 2
if __name__=='__main__': raise SystemExit(main())
