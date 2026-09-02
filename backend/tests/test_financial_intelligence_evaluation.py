from pathlib import Path
from app.evaluation.financial_intelligence import evaluate_financial_intelligence_dataset

def test_release42_evaluation_dataset_has_full_authority_and_citation_compliance():
    root=Path(__file__).resolve().parents[2];r=evaluate_financial_intelligence_dataset(root/'data/evaluation/financial_intelligence_cases.json')
    assert r["cases"]==5 and r["passed"]==5 and r["pass_rate"]==1.0 and r["authority_violations"]==0
