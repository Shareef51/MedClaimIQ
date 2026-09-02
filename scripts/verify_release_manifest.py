#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DIGEST=re.compile(r'^sha256:[0-9a-f]{64}$')

def main():
    p=argparse.ArgumentParser(); p.add_argument('--manifest',required=True); a=p.parse_args()
    path=(ROOT/a.manifest).resolve(); base=(ROOT/'infra/releases').resolve()
    if path.parent!=base or path.suffix!='.json': raise SystemExit('manifest path rejected')
    m=json.loads(path.read_text()); expected=m.pop('manifest_sha256',None)
    actual=hashlib.sha256(json.dumps(m,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if expected!=actual: raise SystemExit('release manifest hash mismatch')
    for x in m['images'].values():
        if not DIGEST.fullmatch(x['digest']): raise SystemExit('floating image reference rejected')
    print(f'release manifest verified: {expected}')
if __name__=='__main__': main()
