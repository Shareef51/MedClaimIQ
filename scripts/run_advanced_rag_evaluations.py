#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.evaluation.advanced_rag import AdvancedRAGEvaluationHarness  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=str(ROOT / "sample-data/advanced_rag_eval_v1.json"))
    parser.add_argument("--output-dir", default=str(ROOT / "artifacts/advanced-rag"))
    parser.add_argument("--gate", action="store_true")
    args = parser.parse_args()
    dataset = json.loads(Path(args.dataset).read_text())
    summary = AdvancedRAGEvaluationHarness().run(dataset)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    payload = summary.as_dict()
    (out / "evaluation.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    rows = "".join(
        f"<tr><td>{html.escape(c.case_id)}</td><td>{'PASS' if c.passed else 'FAIL'}</td><td><pre>{html.escape(json.dumps(c.metrics, sort_keys=True))}</pre></td></tr>"
        for c in summary.cases
    )
    report = f"""<!doctype html><html><head><meta charset='utf-8'><title>MedClaimIQ Advanced RAG Evaluation</title></head>
<body><h1>Advanced RAG Evaluation</h1><p>Decision: <strong>{summary.decision.upper()}</strong></p>
<pre>{html.escape(json.dumps(summary.metrics, indent=2, sort_keys=True))}</pre>
<table border='1' cellpadding='6'><tr><th>Case</th><th>Status</th><th>Metrics</th></tr>{rows}</table></body></html>"""
    (out / "evaluation.html").write_text(report)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 1 if args.gate and summary.decision != "pass" else 0


if __name__ == "__main__":
    raise SystemExit(main())
