#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, re, subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
SHA = re.compile(r"^[0-9a-f]{64}$")


def alembic_head() -> str:
    versions = sorted((ROOT / "backend/alembic/versions").glob("*.py"))
    latest = versions[-1].read_text()
    m = re.search(r'^revision\s*=\s*["\']([^"\']+)', latest, re.M)
    if not m:
        raise SystemExit("unable to determine Alembic head")
    return m.group(1)


def args():
    p=argparse.ArgumentParser()
    p.add_argument('--release-id',required=True); p.add_argument('--git-sha',required=True)
    p.add_argument('--api-repository',required=True); p.add_argument('--api-digest',required=True)
    p.add_argument('--frontend-repository',required=True); p.add_argument('--frontend-digest',required=True)
    p.add_argument('--sbom-sha256',required=True); p.add_argument('--provenance-sha256',required=True)
    p.add_argument('--gate',action='append',default=[],help='name=status; repeatable')
    p.add_argument('--output',default='infra/releases/candidate.json')
    return p.parse_args()


def main():
    a=args()
    if not re.fullmatch(r'[A-Za-z0-9._-]{8,128}', a.release_id): raise SystemExit('unsafe release_id')
    if not re.fullmatch(r'[0-9a-f]{7,64}', a.git_sha): raise SystemExit('git_sha must be lowercase hex')
    for label,value in [('api digest',a.api_digest),('frontend digest',a.frontend_digest)]:
        if not DIGEST.fullmatch(value): raise SystemExit(f'{label} must be immutable sha256 digest')
    for label,value in [('sbom',a.sbom_sha256),('provenance',a.provenance_sha256)]:
        if not SHA.fullmatch(value): raise SystemExit(f'{label} must be SHA-256')
    gates={}
    for item in a.gate:
        name,status=item.split('=',1)
        if status not in {'pass','fail','pending'}: raise SystemExit('invalid gate status')
        gates[name]=status
    manifest={
      'schema_version':'medclaimiq.release.v1','release_id':a.release_id,'git_sha':a.git_sha,
      'created_at':datetime.now(timezone.utc).isoformat(),
      'images':{'api':{'repository':a.api_repository,'digest':a.api_digest},'frontend':{'repository':a.frontend_repository,'digest':a.frontend_digest}},
      'database':{'alembic_head':alembic_head(),'migration_strategy':'expand-contract'},
      'artifacts':{'sbom_sha256':a.sbom_sha256,'provenance_sha256':a.provenance_sha256},'gates':gates,
    }
    canonical=json.dumps(manifest,sort_keys=True,separators=(',',':')).encode(); manifest['manifest_sha256']=hashlib.sha256(canonical).hexdigest()
    out=ROOT/a.output; out.parent.mkdir(parents=True,exist_ok=True)
    if out.exists(): raise SystemExit('release manifest already exists; immutable release IDs cannot be overwritten')
    out.write_text(json.dumps(manifest,indent=2)+'\n')
    print(out); print(manifest['manifest_sha256'])

if __name__=='__main__': main()
