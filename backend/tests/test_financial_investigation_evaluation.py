import json
from pathlib import Path
from app.evaluation.financial_investigation import evaluate_financial_investigation_cases
def test_release43_evaluation_dataset_has_zero_authority_violations():
    p=Path(__file__).resolve().parents[2]/'data/evaluation/financial_investigation_cases.json';cases=json.loads(p.read_text());r=evaluate_financial_investigation_cases(cases)
    assert r['cases']==5 and r['passed']==5 and r['pass_rate']==1 and r['authority_violations']==0
