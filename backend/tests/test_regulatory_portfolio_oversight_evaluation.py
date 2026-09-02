from pathlib import Path
from app.evaluation.regulatory_portfolio_oversight import evaluate

def test_release54_portfolio_oversight_evaluation_dataset_has_zero_authority_violations():
    root=Path(__file__).resolve().parents[2];result=evaluate(root/'artifacts/regulatory-portfolio-oversight/evaluation-dataset.json')
    assert result['cases']==5 and result['passed']==5 and result['authority_violations']==0
