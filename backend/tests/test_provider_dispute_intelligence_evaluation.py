import json
from pathlib import Path
from app.evaluation.provider_dispute_intelligence import evaluate_provider_dispute_cases

def test_release45_evaluation_dataset_is_human_resolution_only_and_passes():
    rows=[json.loads(x) for x in Path("../sample-data/evaluation/provider_dispute_intelligence_cases.jsonl").read_text().splitlines() if x.strip()];result=evaluate_provider_dispute_cases(rows);assert len(rows)>=5 and result["passed"]==len(rows) and result["authority_violations"]==0
