#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,time,urllib.request

def get_json(url,timeout=10):
    req=urllib.request.Request(url,headers={'User-Agent':'MedClaimIQ-release-smoke/1'})
    with urllib.request.urlopen(req,timeout=timeout) as r: return r.status,json.loads(r.read())

def main():
    p=argparse.ArgumentParser(); p.add_argument('--base-url',required=True); p.add_argument('--attempts',type=int,default=12); p.add_argument('--delay',type=float,default=5); a=p.parse_args(); base=a.base_url.rstrip('/')
    checks=['/api/v1/health','/api/v1/release-engineering-model','/api/v1/security-model','/api/v1/evaluation-model']
    failures=[]
    for path in checks:
        last=None
        for _ in range(a.attempts):
            try:
                status,body=get_json(base+path); last=(status,body)
                if status==200: break
            except Exception as e: last=str(e)
            time.sleep(a.delay)
        if not isinstance(last,tuple) or last[0]!=200: failures.append({'path':path,'last':str(last)})
    report={'base_url':base,'checks':checks,'failures':failures,'decision':'pass' if not failures else 'block'}; print(json.dumps(report,indent=2)); return 0 if not failures else 2
if __name__=='__main__': raise SystemExit(main())
