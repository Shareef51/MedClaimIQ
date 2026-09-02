#!/usr/bin/env python3
from __future__ import annotations
import argparse, html, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.evaluation.multimodal_rag import MultimodalRAGEvaluationHarness  # noqa:E402

def main():
    p=argparse.ArgumentParser(); p.add_argument('--dataset',default=str(ROOT/'sample-data/multimodal_rag_eval_v1.json')); p.add_argument('--output-dir',default=str(ROOT/'artifacts/multimodal-rag')); p.add_argument('--gate',action='store_true'); a=p.parse_args()
    summary=MultimodalRAGEvaluationHarness().run(json.loads(Path(a.dataset).read_text())); out=Path(a.output_dir); out.mkdir(parents=True,exist_ok=True); payload=summary.as_dict()
    (out/'evaluation.json').write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n')
    rows=''.join(f"<tr><td>{html.escape(c.case_id)}</td><td>{'PASS' if c.passed else 'FAIL'}</td><td><pre>{html.escape(json.dumps(c.metrics,sort_keys=True))}</pre></td></tr>" for c in summary.cases)
    (out/'evaluation.html').write_text(f"<!doctype html><html><body><h1>Multimodal RAG Evaluation</h1><p><strong>{summary.decision.upper()}</strong></p><pre>{html.escape(json.dumps(summary.metrics,indent=2))}</pre><table border='1'><tr><th>Case</th><th>Status</th><th>Metrics</th></tr>{rows}</table></body></html>")
    print(json.dumps(payload,indent=2,sort_keys=True)); return 1 if a.gate and summary.decision!='pass' else 0
if __name__=='__main__': raise SystemExit(main())
