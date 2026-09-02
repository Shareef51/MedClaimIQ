from app.evaluation.recovery_settlement import evaluate
def test_recovery_settlement_evaluation_dataset_passes_without_authority_violations():
    r=evaluate();assert r=={"cases":5,"passed":5,"pass_rate":1.0,"authority_violations":0}
