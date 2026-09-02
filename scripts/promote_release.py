#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DIGEST=re.compile(r'^sha256:[0-9a-f]{64}$')


def main():
    p=argparse.ArgumentParser(); p.add_argument('--manifest',required=True); p.add_argument('--environment',choices=['staging','production'],required=True); p.add_argument('--strategy',choices=['canary','bluegreen'],default='canary'); a=p.parse_args()
    manifest_path=(ROOT/a.manifest).resolve(); release_root=(ROOT/'infra/releases').resolve()
    if manifest_path.parent != release_root or manifest_path.suffix != '.json': raise SystemExit('manifest must be infra/releases/<name>.json')
    m=json.loads(manifest_path.read_text())
    required=json.loads((ROOT/'config/release_engineering_policy.json').read_text())['gates']['required']
    failures=[g for g in required if m.get('gates',{}).get(g)!='pass']
    if failures: raise SystemExit(f'release gates not passed: {failures}')
    for image in m['images'].values():
        if not DIGEST.fullmatch(image['digest']): raise SystemExit('floating image reference rejected')
    tenant='tenant-staging' if a.environment=='staging' else 'tenant-production'
    gate_json=json.dumps(m.get('gates',{}),sort_keys=True,separators=(',',':'))
    values=f'''images:\n  api:\n    repository: {m["images"]["api"]["repository"]}\n    digest: {m["images"]["api"]["digest"]}\n  frontend:\n    repository: {m["images"]["frontend"]["repository"]}\n    digest: {m["images"]["frontend"]["digest"]}\nrelease:\n  id: {m["release_id"]}\n  gitSha: {m["git_sha"]}\n  alembicHead: {m["database"]["alembic_head"]}\n  manifestSha256: {m.get("manifest_sha256","")}\n  sbomSha256: {m["artifacts"]["sbom_sha256"]}\n  provenanceSha256: {m["artifacts"]["provenance_sha256"]}\n  strategy: {a.strategy}\n  gateSummaryJson: '{gate_json}'\n  auditEnabled: true\n  auditTenantId: {tenant}\n'''
    out=ROOT/f'infra/gitops/environments/{a.environment}/release-values.yaml'; out.write_text(values); print(out)

if __name__=='__main__': main()
