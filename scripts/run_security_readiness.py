#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
POLICY=json.loads((ROOT/'config/security_privacy_policy.json').read_text())

def load_json(path:Path):
    try: return json.loads(path.read_text())
    except Exception: return None

def count_trivy(report):
    counts={'CRITICAL':0,'HIGH':0}
    if not report: return counts
    for result in report.get('Results') or []:
        for v in result.get('Vulnerabilities') or []:
            sev=str(v.get('Severity','')).upper()
            if sev in counts: counts[sev]+=1
        for m in result.get('Misconfigurations') or []:
            sev=str(m.get('Severity','')).upper()
            if sev in counts and str(m.get('Status','FAIL')).upper()!='PASS': counts[sev]+=1
    return counts

def count_semgrep(report):
    counts={'CRITICAL':0,'HIGH':0}
    if not report: return counts
    for r in report.get('results') or []:
        severity=str((r.get('extra') or {}).get('severity','')).upper()
        if severity=='ERROR': counts['HIGH']+=1
    return counts

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--candidate',default='local'); ap.add_argument('--report-dir',default='artifacts/security'); ap.add_argument('--ci',action='store_true'); args=ap.parse_args()
    report_dir=ROOT/args.report_dir; report_dir.mkdir(parents=True,exist_ok=True)
    checks={
      'security_policy': (ROOT/'config/security_privacy_policy.json').exists(),
      'control_mapping': (ROOT/'docs/HIPAA_READY_CONTROL_MAPPING.md').exists(),
      'vendor_inventory': (ROOT/'config/vendor_security_inventory.json').exists(),
      'threat_model': (ROOT/'docs/SECURITY_THREAT_MODEL.md').exists(),
      'incident_runbook': (ROOT/'docs/INCIDENT_RESPONSE_RUNBOOK.md').exists(),
      'gitleaks_config': (ROOT/'.gitleaks.toml').exists(),
      'semgrep_config': (ROOT/'.semgrep.yml').exists(),
      'devsecops_workflow': (ROOT/'.github/workflows/security-readiness-gate.yml').exists(),
      'backend_nonroot': 'USER app' in (ROOT/'backend/Dockerfile').read_text(),
      'frontend_nonroot': 'USER nextjs' in (ROOT/'frontend/Dockerfile').read_text(),
    }
    critical=high=secret_findings=0
    scan_details={}
    for name in ('trivy-fs.json','trivy-backend-image.json','trivy-frontend-image.json'):
        path=report_dir/name
        if path.exists():
            c=count_trivy(load_json(path)); critical+=c['CRITICAL']; high+=c['HIGH']; scan_details[name]=c
        elif args.ci and name == 'trivy-fs.json':
            checks[f'report:{name}']=False
    sem=report_dir/'semgrep.json'
    if sem.exists():
        c=count_semgrep(load_json(sem)); critical+=c['CRITICAL']; high+=c['HIGH']; scan_details['semgrep.json']=c
    elif args.ci: checks['report:semgrep.json']=False
    gitleaks_marker=report_dir/'gitleaks.passed'
    if args.ci: checks['gitleaks_passed']=gitleaks_marker.exists()
    sbom=report_dir/'sbom.cdx.json'
    if args.ci: checks['cyclonedx_sbom']=sbom.exists()
    rate=sum(1 for v in checks.values() if v)/max(1,len(checks))
    gate=POLICY['security_gate']
    decision='pass' if all(checks.values()) and critical<=gate['critical_findings_allowed'] and high<=gate['high_findings_allowed'] and secret_findings<=gate['secret_findings_allowed'] and rate>=gate['required_control_pass_rate'] else 'block'
    result={'candidate':args.candidate,'decision':decision,'run_at':datetime.now(timezone.utc).isoformat(),'controls_version':POLICY['version'],'control_pass_rate':round(rate,4),'critical_findings':critical,'high_findings':high,'secret_findings':secret_findings,'checks':checks,'scan_details':scan_details}
    canonical=json.dumps(result,sort_keys=True,separators=(',',':')).encode(); result['report_sha256']=hashlib.sha256(canonical).hexdigest()
    out=report_dir/'readiness.json'; out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n'); print(json.dumps(result,indent=2)); raise SystemExit(0 if decision=='pass' else 2)
if __name__=='__main__': main()
