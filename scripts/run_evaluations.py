from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"backend"))
from app.evaluation.harness import GoldenEvaluationHarness
from app.evaluation.reports import write_html_report,write_json_report
from app.services.evaluation import load_dataset,load_policy
p=argparse.ArgumentParser();p.add_argument("--dataset",default="golden_claims_v1");p.add_argument("--candidate",default="working-tree");p.add_argument("--report-dir",default="artifacts/evaluations");p.add_argument("--gate",action="store_true");args=p.parse_args()
dataset=load_dataset(args.dataset);summary=GoldenEvaluationHarness(load_policy()).run(dataset,args.candidate,dataset.get("baseline_metrics"));out=ROOT/args.report_dir;write_json_report(summary,out/"evaluation.json");write_html_report(summary,out/"evaluation.html");print(json.dumps({"decision":summary.decision.value,"pass_rate":summary.pass_rate,"run_id":summary.run_id,"report_dir":str(out)},indent=2));sys.exit(2 if args.gate and summary.decision.value!="pass" else 0)
