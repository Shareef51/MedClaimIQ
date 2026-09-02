from pathlib import Path
from app.evaluation.recovery_settlement_intelligence import evaluate
def test_release48_evaluation_dataset_has_zero_authority_violations():
    path=Path(__file__).resolve().parents[2]/'artifacts/recovery-settlement-intelligence/evaluation-dataset.json';r=evaluate(path);assert r=={"cases":5,"passed":5,"pass_rate":1.0,"authority_violations":0}
