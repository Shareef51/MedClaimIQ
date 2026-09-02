from pathlib import Path
from app.evaluation.recovery_control_assurance import evaluate

def test_release49_evaluation_dataset_has_zero_authority_violations():
    path=Path(__file__).resolve().parents[2]/'artifacts/recovery-control-assurance/evaluation-dataset.json';r=evaluate(path);assert r=={"cases":5,"passed":5,"pass_rate":1.0,"authority_violations":0}
