#!/usr/bin/env python3
from pathlib import Path
import json,re,hashlib,sys
ROOT=Path(__file__).resolve().parents[1]
exclude={'.git','.venv','node_modules','__pycache__'}
patterns={
 'private_key':re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
 'openai_key':re.compile(r'\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b'),
 'aws_access_key':re.compile(r'\bAKIA[0-9A-Z]{16}\b'),
}
findings=[]
for path in ROOT.rglob('*'):
    if not path.is_file() or any(x in exclude for x in path.parts): continue
    if path.suffix.lower() in {'.png','.jpg','.jpeg','.gif','.webp','.zip','.pdf','.pyc'}: continue
    try:text=path.read_text(errors='ignore')
    except Exception: continue
    for kind,rx in patterns.items():
        for m in rx.finditer(text): findings.append({'kind':kind,'path':str(path.relative_to(ROOT)),'line':text.count('\n',0,m.start())+1})
checks={
 'backend_nonroot':'USER app' in (ROOT/'backend/Dockerfile').read_text(),
 'frontend_nonroot':'USER nextjs' in (ROOT/'frontend/Dockerfile').read_text(),
 'network_policy':(ROOT/'infra/helm/medclaimiq/templates/networkpolicy.yaml').exists(),
 'security_headers_middleware':(ROOT/'backend/app/middleware/security_headers.py').exists(),
 'oidc_rs256_default':'oidc_allowed_algorithms: str = "RS256"' in (ROOT/'backend/app/core/config.py').read_text(),
 'gitleaks_config':(ROOT/'.gitleaks.toml').exists(),
 'semgrep_config':(ROOT/'.semgrep.yml').exists(),
 'security_workflow':(ROOT/'.github/workflows/security-readiness-gate.yml').exists(),
}
result={'checks':checks,'credential_pattern_findings':findings,'passed':all(checks.values()) and not findings}
canonical=json.dumps(result,sort_keys=True,separators=(',',':')).encode();result['sha256']=hashlib.sha256(canonical).hexdigest()
out=ROOT/'artifacts/security/local_security_baseline.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));raise SystemExit(0 if result['passed'] else 2)
