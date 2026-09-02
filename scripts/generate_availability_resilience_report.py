#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(); p.add_argument('--report-dir',default=str(ROOT/'artifacts/performance')); a=p.parse_args(); d=Path(a.report_dir)
    perf=json.loads((d/'performance-gate.json').read_text()); res=json.loads((d/'resilience-gate.json').read_text()); cap=json.loads((d/'capacity-model.json').read_text()); policy=json.loads((ROOT/'config/performance_resilience_policy.json').read_text())
    availability=policy['resilience']['availability_target']; experiments=res['experiments']; recoveries=[float(x['recovery_seconds']) for x in experiments if x.get('recovery_seconds') is not None]
    report={'schema_version':'availability-resilience-report-v1','generated_at':datetime.now(timezone.utc).isoformat(),'availability_target':availability,'performance_decision':perf['decision'],'resilience_decision':res['decision'],'critical_resilience_failures':len(res['failed_experiments']),'experiment_count':len(experiments),'max_observed_recovery_seconds':max(recoveries) if recoveries else None,'capacity_model':cap['capacity'],'release_recommendation':'pass' if perf['decision']=='pass' and res['decision']=='pass' else 'block','disclaimer':'synthetic/check-in evidence is not a contractual availability result; production availability requires deployed-environment SLI measurement'}
    (d/'availability-resilience-report.json').write_text(json.dumps(report,indent=2))
    (d/'availability-resilience-report.html').write_text(f"<!doctype html><html><body><h1>Availability & Resilience: {report['release_recommendation'].upper()}</h1><p>Target availability: {availability:.3%}</p><p>Critical resilience failures: {report['critical_resilience_failures']}</p><p>Max observed synthetic recovery: {report['max_observed_recovery_seconds']} s</p><p>{report['disclaimer']}</p></body></html>")
    print('availability/resilience report:',report['release_recommendation'].upper())
if __name__=='__main__': main()
