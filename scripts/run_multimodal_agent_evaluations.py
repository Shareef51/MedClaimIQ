#!/usr/bin/env python
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"backend"))
from app.evaluation.multimodal_agents import evaluate_multimodal_agent_contracts
r=evaluate_multimodal_agent_contracts(); out=Path("artifacts/multimodal-agents");out.mkdir(parents=True,exist_ok=True)
(out/"evaluation.json").write_text(json.dumps(r,indent=2)+"\n")
(out/"evaluation.html").write_text(f"<html><body><h1>Multimodal Agent Evaluation</h1><p>Decision: {'PASS' if r['passed'] else 'BLOCK'}</p><p>Accuracy: {r['value']:.2f}</p></body></html>\n")
print(json.dumps(r,sort_keys=True)); raise SystemExit(0 if r['passed'] else 2)
