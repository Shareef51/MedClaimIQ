from __future__ import annotations
import html,json
from dataclasses import asdict
from pathlib import Path
from app.evaluation.domain import EvaluationSummary

def summary_to_dict(summary):return asdict(summary)
def write_json_report(summary:EvaluationSummary,path:Path):path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(summary_to_dict(summary),indent=2,default=str)+"\n"); return path
def write_html_report(summary:EvaluationSummary,path:Path):
    path.parent.mkdir(parents=True,exist_ok=True)
    rows="".join(f"<tr><td>{html.escape(m.metric)}</td><td>{m.value:.6f}</td><td>{m.details.get('baseline_value','')}</td><td>{m.details.get('delta','')}</td><td>{'' if m.threshold is None else m.threshold}</td><td>{'PASS' if m.passed else 'FAIL'}</td></tr>" for m in summary.metrics)
    cases="".join(f"<tr><td>{html.escape(c.case_id)}</td><td>{html.escape(c.suite)}</td><td>{'PASS' if c.passed else 'FAIL'}</td><td>{c.latency_ms:.1f}</td><td>${c.estimated_cost_usd:.6f}</td></tr>" for c in summary.cases)
    reasons="<br>".join(html.escape(r) for r in summary.regression_reasons) or "None"
    doc=("<!doctype html><html><head><meta charset='utf-8'><title>MedClaimIQ Evaluation</title><style>body{font-family:system-ui;margin:2rem;max-width:1100px}table{border-collapse:collapse;width:100%}th,td{border:1px solid #ddd;padding:.5rem;text-align:left}</style></head><body>"+f"<h1>MedClaimIQ AI Quality Report</h1><h2>Release gate: {summary.decision.value.upper()}</h2><p>Dataset {html.escape(summary.dataset_version)} · Candidate {html.escape(summary.candidate_version)}</p><h2>Metrics</h2><table><tr><th>Metric</th><th>Value</th><th>Baseline</th><th>Delta</th><th>Threshold</th><th>Gate</th></tr>{rows}</table><h2>Cases</h2><table><tr><th>Case</th><th>Suite</th><th>Status</th><th>Latency ms</th><th>Est. cost</th></tr>{cases}</table><h2>Regression / gate reasons</h2><p>{reasons}</p><p>Config SHA-256: {summary.config_sha256}</p></body></html>")
    path.write_text(doc); return path
